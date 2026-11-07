import os
import tempfile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Torre, Apartamento, MedicaoMensal
from .ia_vistoria import analisar_video_obra

def garantir_usuario_adm():
    """Cria automaticamente o usuário 'adm' com senha 'obra2026' se não existir"""
    if not User.objects.filter(username='adm').exists():
        User.objects.create_superuser('adm', 'adm@horizontesgo.com.br', 'obra2026')

def login_sistema(request):
    garantir_usuario_adm()
    if request.user.is_authenticated:
        return redirect('painel_principal')

    erro = None
    if request.method == 'POST':
        usuario = request.POST.get('username', '').strip()
        senha = request.POST.get('password', '').strip()
        user = authenticate(request, username=usuario, password=senha)
        if user is not None:
            login(request, user)
            return redirect('painel_principal')
        else:
            erro = "Acesso negado: usuário ou senha incorretos."

    return render(request, 'obras/login.html', {'erro': erro})

def logout_sistema(request):
    logout(request)
    return redirect('login_sistema')

@login_required(login_url='login_sistema')
def painel_principal(request):
    mes_selecionado = request.GET.get('mes', '2026-11')
    torre_selecionada = request.GET.get('torre', 'TODAS')
    andar_selecionado = request.GET.get('andar', 'TODOS')

    torres = Torre.objects.all()
    medicoes_mes_atual = MedicaoMensal.objects.filter(mes_referencia=mes_selecionado).select_related('apartamento__torre')
    medicoes_mes_anterior = MedicaoMensal.objects.filter(mes_referencia='2026-10').select_related('apartamento__torre')

    if torre_selecionada != 'TODAS':
        medicoes_mes_atual = medicoes_mes_atual.filter(apartamento__torre__id=torre_selecionada)
        medicoes_mes_anterior = medicoes_mes_anterior.filter(apartamento__torre__id=torre_selecionada)

    if andar_selecionado != 'TODOS':
        medicoes_mes_atual = medicoes_mes_atual.filter(apartamento__andar=int(andar_selecionado))
        medicoes_mes_anterior = medicoes_mes_anterior.filter(apartamento__andar=int(andar_selecionado))

    total_med = medicoes_mes_atual.count()
    avanco_atual = round(sum(m.percentual_concluido for m in medicoes_mes_atual) / total_med, 1) if total_med > 0 else 0.0

    total_ant = medicoes_mes_anterior.count()
    avanco_anterior = round(sum(m.percentual_concluido for m in medicoes_mes_anterior) / total_ant, 1) if total_ant > 0 else 0.0

    ritmo_mensal = round(avanco_atual - avanco_anterior, 1) if mes_selecionado == '2026-11' else round(avanco_atual * 0.15, 1)
    falta_construir = max(0.0, round(100.0 - avanco_atual, 1))
    meses_para_terminar = round(falta_construir / ritmo_mensal, 1) if ritmo_mensal > 0 else 0.0

    unidades_iso_ok = sum(1 for m in medicoes_mes_atual if m.cor_status() == 'green')
    unidades_trava = sum(1 for m in medicoes_mes_atual if m.cor_status() == 'yellow')
    unidades_rnc = sum(1 for m in medicoes_mes_atual if m.cor_status() == 'red')

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

    context = {
        'torres': torres,
        'resumo_torres': resumo_torres,
        'matriz_andares': matriz_andares,
        'mes_selecionado': mes_selecionado,
        'torre_selecionada': torre_selecionada,
        'andar_selecionado': andar_selecionado,
        'andares_disponiveis': range(6, 0, -1),
        'avanco_atual': avanco_atual,
        'ritmo_mensal': ritmo_mensal,
        'falta_construir': falta_construir,
        'meses_para_terminar': meses_para_terminar,
        'unidades_iso_ok': unidades_iso_ok,
        'unidades_trava': unidades_trava,
        'unidades_rnc': unidades_rnc,
    }
    return render(request, 'obras/painel.html', context)

@login_required(login_url='login_sistema')
def popular_dados_demo(request):
    if request.method == 'POST':
        Torre.objects.all().delete()
        for nome_torre, fator in [("Torre A - Norte", 1.0), ("Torre B - Sul", 0.75)]:
            torre = Torre.objects.create(nome=nome_torre, total_andares=6)
            for andar in range(1, 7):
                for final in range(1, 7):
                    num_apto = f"{andar}0{final}"
                    apto = Apartamento.objects.create(torre=torre, andar=andar, numero=num_apto)

                    if final == 6:
                        pct_nov, status_nov, etapa = int(55 * fator), 'NAO_CONFORME', 'Alvenaria (Falha FVS)'
                        laudo = 'IA detectou falha no encunhamento e ausência de verga na janela.'
                    elif final == 5 and andar <= 4:
                        pct_nov, status_nov, etapa = 90, 'PENDENTE', 'Acabamento (Aguardando FVS)'
                        laudo = 'Serviço físico executado, mas travado em 90% aguardando assinatura da FVS.'
                    elif andar <= 2:
                        pct_nov, status_nov, etapa = 100, 'CONFORME', 'Pintura e Acabamento Final'
                        laudo = 'Apartamento 100% concluído e validado sem pendências na ISO 9001.'
                    elif andar <= 4:
                        pct_nov, status_nov, etapa = int(70 * fator), 'CONFORME', 'Reboco e Contrapiso'
                        laudo = 'Reboco interno e caixas elétricas 4x2 aprovadas no vídeo.'
                    else:
                        pct_nov, status_nov, etapa = int(45 * fator), 'CONFORME', 'Alvenaria e Tubulação'
                        laudo = 'Marcação e elevação de alvenaria dentro do prumo.'

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
def avaliar_apartamento(request, medicao_id):
    if request.method == 'POST':
        medicao = get_object_or_404(MedicaoMensal, id=medicao_id)
        acao = request.POST.get('acao')

        if acao == 'ia_video' and request.FILES.get('video_vistoria'):
            video = request.FILES['video_vistoria']
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                    for chunk in video.chunks():
                        tmp.write(chunk)
                    temp_path = tmp.name

                laudo = analisar_video_obra(temp_path, medicao.apartamento.numero, medicao.requisito_iso)
                medicao.etapa_atual = laudo.etapa_identificada
                medicao.percentual_concluido = laudo.percentual_sugerido
                medicao.status_iso = laudo.status_iso_sugerido
                medicao.laudo_ia = laudo.resumo_tecnico
                trava = medicao.salvar_com_trava_iso()

                if trava:
                    messages.warning(request, f"🔒 IA sugeriu 100% no Apto {medicao.apartamento.numero}, mas a Trava ISO 9001 manteve em 90%!")
                else:
                    messages.success(request, f"🤖 Vídeo do Apto {medicao.apartamento.numero} avaliado pela IA: {medicao.percentual_concluido}% ({medicao.status_iso})!")
            except Exception as e:
                messages.error(request, f"Erro na leitura da IA: {e}")
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            medicao.percentual_concluido = int(request.POST.get('percentual', medicao.percentual_concluido))
            medicao.status_iso = request.POST.get('status_iso', medicao.status_iso)
            medicao.etapa_atual = request.POST.get('etapa_atual', medicao.etapa_atual)
            medicao.laudo_ia = request.POST.get('laudo_ia', medicao.laudo_ia)
            trava = medicao.salvar_com_trava_iso()
            if trava:
                messages.warning(request, f"🔒 TRAVA ISO 9001 ATIVA: Apto {medicao.apartamento.numero} bloqueado em 90% até a FVS ficar CONFORME.")
            else:
                messages.info(request, f"✅ Apto {medicao.apartamento.numero} atualizado com sucesso!")

    return redirect(request.META.get('HTTP_REFERER', 'painel_principal'))