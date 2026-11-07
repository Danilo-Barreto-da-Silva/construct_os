import os
import tempfile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from .models import Torre, Apartamento, MedicaoMensal, HistoricoMedicao, NaoConformidade, PlanejamentoMensal
from .ia_vistoria import analisar_video_obra
from .curva_s import consolidar_curva

def login_sistema(request):
    if request.user.is_authenticated:
        return redirect('painel_principal')

    erro = None
    if request.method == 'POST':
        usuario = request.POST.get('username', '').strip()
        senha = request.POST.get('password', '')
        user = authenticate(request, username=usuario, password=senha)
        if user is not None:
            login(request, user)
            destino = request.POST.get('next', '')
            if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                destino = '/'
            return redirect(destino)
        else:
            erro = "Acesso negado: usuário ou senha incorretos."

    return render(request, 'obras/login.html', {'erro': erro, 'next': request.GET.get('next', '')})

@require_POST
def logout_sistema(request):
    logout(request)
    return redirect('login_sistema')

@login_required(login_url='login_sistema')
def painel_principal(request):
    mes_selecionado = request.GET.get('mes', timezone.localdate().strftime('%Y-%m'))
    meses_disponiveis = list(MedicaoMensal.objects.order_by('-mes_referencia').values_list('mes_referencia', flat=True).distinct())
    if 'mes' not in request.GET and meses_disponiveis:
        mes_selecionado = meses_disponiveis[0]
    if mes_selecionado not in meses_disponiveis and meses_disponiveis:
        mes_selecionado = meses_disponiveis[0]
    torre_selecionada = request.GET.get('torre', 'TODAS')
    andar_selecionado = request.GET.get('andar', 'TODOS')

    torres = Torre.objects.all()
    medicoes_mes_atual = MedicaoMensal.objects.filter(mes_referencia=mes_selecionado).select_related('apartamento__torre')
    try:
        ano, mes = map(int, mes_selecionado.split('-'))
        mes_anterior = f'{ano - 1}-12' if mes == 1 else f'{ano}-{mes - 1:02d}'
    except (ValueError, TypeError):
        mes_anterior = ''
    medicoes_mes_anterior = MedicaoMensal.objects.filter(mes_referencia=mes_anterior).select_related('apartamento__torre')

    if torre_selecionada != 'TODAS' and not torre_selecionada.isdecimal():
        torre_selecionada = 'TODAS'

    if torre_selecionada != 'TODAS':
        medicoes_mes_atual = medicoes_mes_atual.filter(apartamento__torre__id=torre_selecionada)
        medicoes_mes_anterior = medicoes_mes_anterior.filter(apartamento__torre__id=torre_selecionada)

    andar_num = None
    if andar_selecionado != 'TODOS':
        try:
            andar_num = int(andar_selecionado)
        except ValueError:
            andar_num = None
        medicoes_mes_atual = medicoes_mes_atual.filter(apartamento__andar=andar_num)
        medicoes_mes_anterior = medicoes_mes_anterior.filter(apartamento__andar=andar_num)

    unidades_filtro = Apartamento.objects.all()
    if torre_selecionada != 'TODAS':
        unidades_filtro = unidades_filtro.filter(torre_id=int(torre_selecionada))
    if andar_selecionado != 'TODOS':
        unidades_filtro = unidades_filtro.filter(andar=andar_num) if andar_num is not None else unidades_filtro.none()
    total_unidades = unidades_filtro.count()

    total_med = medicoes_mes_atual.count()
    avanco_atual = round(sum(m.percentual_concluido for m in medicoes_mes_atual) / total_med, 1) if total_med > 0 else 0.0
    cobertura_completa = total_unidades > 0 and total_med == total_unidades

    total_ant = medicoes_mes_anterior.count()
    avanco_anterior = round(sum(m.percentual_concluido for m in medicoes_mes_anterior) / total_ant, 1) if total_ant > 0 else 0.0
    atuais_ids = set(medicoes_mes_atual.values_list('apartamento_id', flat=True))
    anteriores_ids = set(medicoes_mes_anterior.values_list('apartamento_id', flat=True))
    # Não comparar meses com grupos diferentes ou cobertura incompleta:
    # médias parciais poderiam simular progresso ou retrocesso inexistente.
    ritmo_mensal = (
        round(avanco_atual - avanco_anterior, 1)
        if cobertura_completa and atuais_ids and atuais_ids == anteriores_ids
        else None
    )
    falta_construir = max(0.0, round(100.0 - avanco_atual, 1))
    meses_para_terminar = round(falta_construir / ritmo_mensal, 1) if ritmo_mensal is not None and ritmo_mensal > 0 else None

    unidades_iso_ok = sum(1 for m in medicoes_mes_atual if m.percentual_concluido == 100 and m.status_iso == 'CONFORME')
    fvs_conformes = sum(1 for m in medicoes_mes_atual if m.status_iso == 'CONFORME')
    unidades_trava = sum(1 for m in medicoes_mes_atual if m.status_iso == 'PENDENTE')
    unidades_rnc = sum(1 for m in medicoes_mes_atual if m.status_iso == 'NAO_CONFORME')

    # Série histórica: somente medições efetivamente cadastradas, sem pontos inventados.
    historico = MedicaoMensal.objects.filter(mes_referencia__lte=mes_selecionado)
    if torre_selecionada != 'TODAS':
        historico = historico.filter(apartamento__torre_id=int(torre_selecionada))
    if andar_selecionado != 'TODOS' and andar_num is not None:
        historico = historico.filter(apartamento__andar=andar_num)
    from django.db.models import Avg
    historico_mensal = list(
        historico.values('mes_referencia').annotate(avanco=Avg('percentual_concluido')).order_by('mes_referencia')
    )
    meses_grafico = [item['mes_referencia'] for item in historico_mensal]
    valores_grafico = [round(item['avanco'], 1) for item in historico_mensal]
    # A amostra pode mudar entre meses. Exibir sua cobertura e não unir
    # médias de populações diferentes como se fossem uma mesma série contínua.
    cobertura_grafico = [
        {
            'mes': item['mes_referencia'],
            'quantidade': historico.filter(mes_referencia=item['mes_referencia']).count(),
            'total': total_unidades,
        }
        for item in historico_mensal
    ]

    # Meta só é exibida quando explicitamente cadastrada.
    # Comparação de metas por torre não vale para filtros exclusivos de pavimento.
    metas_query = PlanejamentoMensal.objects.filter(mes_referencia__in=meses_grafico)
    if torre_selecionada != 'TODAS':
        metas_query = metas_query.filter(torre_id=int(torre_selecionada))
    metas_por_mes = {}
    for meta in metas_query:
        metas_por_mes.setdefault(meta.mes_referencia, {})[meta.torre_id] = float(meta.percentual_planejado)

    metas_grafico = []
    if andar_selecionado != 'TODOS':
        metas_grafico = [None for _ in meses_grafico]
    elif torre_selecionada != 'TODAS':
        metas_grafico = [
            metas_por_mes.get(mes, {}).get(int(torre_selecionada))
            for mes in meses_grafico
        ]
    else:
        ids_torres = set(torres.values_list('id', flat=True))
        for mes in meses_grafico:
            metas_mes = metas_por_mes.get(mes, {})
            if ids_torres and ids_torres.issubset(metas_mes.keys()):
                metas_grafico.append(round(
                    sum(metas_mes[id_torre] for id_torre in ids_torres) / len(ids_torres), 2
                ))
            else:
                metas_grafico.append(None)

    # Oculta metas em meses com cobertura física parcial do conjunto de unidades.
    for indice, mes in enumerate(meses_grafico):
        qtd_mes = historico.filter(mes_referencia=mes).count()
        if qtd_mes != total_unidades:
            metas_grafico[indice] = None

    rncs_formais_abertas = NaoConformidade.objects.exclude(
        situacao='RESOLVIDA'
    ).count()
    rncs_sem_formalizacao = MedicaoMensal.objects.filter(
        mes_referencia=mes_selecionado, status_iso='NAO_CONFORME',
        rncs__isnull=True,
    ).count()

    resumo_torres = []
    for t in torres:
        meds_t = MedicaoMensal.objects.filter(mes_referencia=mes_selecionado, apartamento__torre=t)
        qtd = meds_t.count()
        media_t = round(sum(m.percentual_concluido for m in meds_t) / qtd, 1) if qtd > 0 else 0
        rncs_t = meds_t.filter(status_iso='NAO_CONFORME').count()
        resumo_torres.append({'torre': t, 'avanco': media_t, 'rncs': rncs_t, 'total_aptos': qtd})

    matriz_andares = {}
    for med in medicoes_mes_atual.order_by('-apartamento__andar', 'apartamento__numero'):
        andar_num = med.apartamento.andar
        matriz_andares.setdefault(andar_num, []).append(med)

    # A Curva S de serviços é própria de cada torre. Nunca misturá-la
    # com a média de apartamentos nem com um filtro de pavimento.
    curva_servicos = None
    if torre_selecionada != 'TODAS' and andar_selecionado == 'TODOS':
        torre_fisica = torres.filter(pk=int(torre_selecionada)).first()
        if torre_fisica and torre_fisica.servicos_fisicos.exists():
            curva_servicos = consolidar_curva(torre_fisica)

    context = {
        'curva_servicos': curva_servicos,
        'torres': torres,
        'meses_grafico': meses_grafico,
        'valores_grafico': valores_grafico,
        'cobertura_grafico': cobertura_grafico,
        'metas_grafico': metas_grafico,
        'existe_planejamento': any(valor is not None for valor in metas_grafico),
        'rncs_formais_abertas': rncs_formais_abertas,
        'rncs_sem_formalizacao': rncs_sem_formalizacao,
        'meses_disponiveis': meses_disponiveis,
        'ia_configurada': settings.GEMINI_API_KEY != 'MODO_SIMULACAO',
        'pode_gerar_demo': request.user.is_superuser and settings.DEBUG and not Torre.objects.exists(),
        'resumo_torres': resumo_torres,
        'matriz_andares': matriz_andares,
        'mes_selecionado': mes_selecionado,
        'torre_selecionada': torre_selecionada,
        'andar_selecionado': andar_selecionado,
        'andares_disponiveis': sorted(set(Apartamento.objects.values_list('andar', flat=True)), reverse=True),
        'avanco_atual': avanco_atual,
        'total_med': total_med,
        'total_unidades': total_unidades,
        'cobertura_completa': cobertura_completa,
        'ritmo_mensal': ritmo_mensal,
        'falta_construir': falta_construir,
        'meses_para_terminar': meses_para_terminar,
        'unidades_iso_ok': unidades_iso_ok,
        'fvs_conformes': fvs_conformes,
        'unidades_trava': unidades_trava,
        'unidades_rnc': unidades_rnc,
    }
    return render(request, 'obras/painel.html', context)

@login_required(login_url='login_sistema')
@require_POST
def popular_dados_demo(request):
    if not (request.user.is_superuser and settings.DEBUG):
        raise PermissionDenied
    if request.POST.get('confirmar_substituicao') != 'SIM':
        messages.error(request, 'Confirme explicitamente a substituição dos dados de demonstração.')
        return redirect('painel_principal')
    if request.method == 'POST':
        if Torre.objects.exists():
            messages.error(request, 'Geração bloqueada: já existem torres cadastradas. Nenhum dado foi apagado.')
            return redirect('painel_principal')
        for nome_torre, fator in [("Torre A - Norte", 1.0), ("Torre B - Sul", 0.75)]:
            torre = Torre.objects.create(nome=nome_torre, total_andares=6)
            for andar in range(1, 7):
                for final in range(1, 7):
                    num_apto = f"{andar}0{final}"
                    apto = Apartamento.objects.create(torre=torre, andar=andar, numero=num_apto)

                    if final == 6:
                        pct_nov, status_nov, etapa = int(55 * fator), 'NAO_CONFORME', 'Alvenaria (Falha FVS)'
                        laudo = '[EXEMPLO FICTÍCIO] Falha simulada no encunhamento e ausência de verga na janela.'
                    elif final == 5 and andar <= 4:
                        pct_nov, status_nov, etapa = 90, 'PENDENTE', 'Acabamento (Aguardando FVS)'
                        laudo = '[EXEMPLO FICTÍCIO] Execução simulada com FVS pendente; avanço físico independente do aceite.'
                    elif andar <= 2:
                        pct_nov, status_nov, etapa = 100, 'CONFORME', 'Pintura e Acabamento Final'
                        laudo = '[EXEMPLO FICTÍCIO] Registro demonstrativo de serviço concluído e conforme.'
                    elif andar <= 4:
                        pct_nov, status_nov, etapa = int(70 * fator), 'CONFORME', 'Reboco e Contrapiso'
                        laudo = '[EXEMPLO FICTÍCIO] Reboco e caixas elétricas simulados como aprovados.'
                    else:
                        pct_nov, status_nov, etapa = int(45 * fator), 'CONFORME', 'Alvenaria e Tubulação'
                        laudo = '[EXEMPLO FICTÍCIO] Marcação e elevação de alvenaria simuladas.'

                    pct_out = max(0, pct_nov - 12)

                    MedicaoMensal.objects.create(
                        apartamento=apto, mes_referencia='2026-10',
                        etapa_atual=etapa, percentual_concluido=pct_out,
                        status_iso='CONFORME' if pct_out == 100 else 'PENDENTE',
                        laudo_ia='Medição fechada do mês de Outubro.'
                    )
                    MedicaoMensal.objects.create(
                        apartamento=apto, mes_referencia='2026-11',
                        etapa_atual=etapa, percentual_concluido=pct_nov,
                        status_iso=status_nov, laudo_ia=laudo
                    )

        messages.success(request, "⚡ Obra completa gerada (Torre A + Torre B, 6 andares e histórico Out/Nov)!")
    return redirect('painel_principal')

@login_required(login_url='login_sistema')
def historico_medicao(request, medicao_id):
    medicao = get_object_or_404(
        MedicaoMensal.objects.select_related('apartamento__torre', 'fvs_aprovada_por'),
        pk=medicao_id,
    )
    registros = medicao.historico.select_related('autor').all()
    return render(request, 'obras/historico_medicao.html', {
        'medicao': medicao,
        'registros': registros,
    })


@login_required(login_url='login_sistema')
@require_POST
def avaliar_apartamento(request, medicao_id):
    medicao = get_object_or_404(MedicaoMensal, pk=medicao_id)
    acao = request.POST.get('acao')

    if acao == 'ia_video':
        video = request.FILES.get('video_vistoria')
        if not video:
            messages.error(request, 'Selecione um vídeo antes de solicitar análise.')
        elif video.size > 30 * 1024 * 1024:
            messages.error(request, 'Vídeo excede o limite de 30 MB.')
        elif not video.name.lower().endswith(('.mp4', '.mov', '.webm')):
            messages.error(request, 'Formato não permitido. Utilize MP4, MOV ou WebM.')
        elif video.content_type not in (
                'video/mp4', 'video/quicktime', 'video/webm', 'application/octet-stream'):
            messages.error(request, 'O arquivo selecionado não foi identificado como vídeo.')
        elif settings.GEMINI_API_KEY == 'MODO_SIMULACAO':
            messages.error(request, 'Configure GEMINI_API_KEY para analisar vídeos reais.')
        else:
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    for chunk in video.chunks():
                        tmp.write(chunk)
                    temp_path = tmp.name

                laudo = analisar_video_obra(
                    temp_path, medicao.apartamento.numero, medicao.requisito_iso
                )
                sugestao = (
                    f"Etapa sugerida: {laudo.etapa_identificada}\n"
                    f"Avanço sugerido: {laudo.percentual_sugerido}%\n"
                    f"Status sugerido: {laudo.status_iso_sugerido}\n"
                    f"Análise: {laudo.resumo_tecnico}"
                )
                with transaction.atomic():
                    medicao = MedicaoMensal.objects.select_for_update().get(pk=medicao_id)
                    medicao.sugestao_ia = sugestao
                    medicao.save(update_fields=['sugestao_ia'])
                    HistoricoMedicao.objects.create(
                        medicao=medicao, autor=request.user, origem='SUGESTAO_IA',
                        percentual_anterior=medicao.percentual_concluido,
                        percentual_novo=medicao.percentual_concluido,
                        status_anterior=medicao.status_iso,
                        status_novo=medicao.status_iso,
                        etapa_anterior=medicao.etapa_atual,
                        etapa_nova=medicao.etapa_atual,
                        observacao=sugestao[:2000],
                    )
                messages.info(
                    request,
                    'Sugestão registrada no histórico. A medição e a FVS não foram alteradas.'
                )
            except Exception:
                messages.error(
                    request,
                    'Não foi possível analisar o vídeo. Confira a configuração e tente novamente.'
                )
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

    elif acao == 'manual':
        try:
            percentual = int(request.POST.get('percentual', ''))
            status = request.POST.get('status_iso', '')
            etapa = request.POST.get('etapa_atual', '').strip()
            observacao = request.POST.get('laudo_ia', '').strip()

            if not 0 <= percentual <= 100:
                raise ValueError('Percentual deve estar entre 0 e 100.')
            if status not in dict(MedicaoMensal.STATUS_ISO):
                raise ValueError('Status de FVS inválido.')
            if not etapa or len(etapa) > 100:
                raise ValueError('Informe uma etapa com até 100 caracteres.')
            if status == 'CONFORME' and not request.user.is_staff:
                raise PermissionDenied('Somente um membro autorizado pode registrar FVS conforme.')
            if status != 'NAO_CONFORME' and medicao.rncs.exclude(
                    situacao='RESOLVIDA').exists():
                raise ValueError(
                    'Existem RNCs formais abertas. A FVS permanece não conforme até tratamento.'
                )
            if status == 'CONFORME' and medicao.itens_fvs.exclude(
                    resultado__in=['CONFORME', 'NA']).exists():
                raise ValueError('Existem itens de FVS não aprovados ou não verificados.')

            with transaction.atomic():
                medicao = MedicaoMensal.objects.select_for_update().get(pk=medicao_id)
                percentual_anterior = medicao.percentual_concluido
                status_anterior = medicao.status_iso
                etapa_anterior = medicao.etapa_atual
                observacao_anterior = medicao.laudo_ia

                medicao.percentual_concluido = percentual
                medicao.status_iso = status
                medicao.etapa_atual = etapa
                medicao.laudo_ia = observacao

                if status == 'CONFORME':
                    # Registro de aprovação administrativa; não é assinatura digital.
                    if (status_anterior != 'CONFORME' or
                            percentual != percentual_anterior or
                            etapa != etapa_anterior or
                            observacao != observacao_anterior or
                            medicao.fvs_aprovada_por_id is None):
                        medicao.fvs_aprovada_por = request.user
                        medicao.fvs_aprovada_em = timezone.now()
                else:
                    medicao.fvs_aprovada_por = None
                    medicao.fvs_aprovada_em = None

                medicao.full_clean()
                medicao.save()

                if (percentual != percentual_anterior or status != status_anterior or
                        etapa != etapa_anterior or observacao != observacao_anterior):
                    HistoricoMedicao.objects.create(
                        medicao=medicao, autor=request.user, origem='MANUAL',
                        percentual_anterior=percentual_anterior,
                        percentual_novo=percentual,
                        status_anterior=status_anterior,
                        status_novo=status,
                        etapa_anterior=etapa_anterior,
                        etapa_nova=etapa,
                        observacao=observacao[:2000],
                    )

            messages.success(
                request,
                f'Medição do apartamento {medicao.apartamento.numero} registrada. '
                'Consulte o histórico para conferir as alterações.'
            )
        except (ValueError, ValidationError) as exc:
            messages.error(request, f'Dados inválidos: {exc}')
    else:
        messages.error(request, 'Ação não reconhecida.')

    destino = request.META.get('HTTP_REFERER', '')
    if not url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        destino = '/'
    return redirect(destino)
