"""Relatórios resumidos e exportação CSV protegida para equipe autorizada."""
import csv

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .models import MedicaoMensal, NaoConformidade, Torre, MarcoServico, PlanejamentoMensal, validar_mes_referencia
from .curva_s import consolidar_curva


def selecionar_filtros(request):
    # Relatórios aceitam meses oriundos das medições por apartamento OU
    # dos lançamentos por serviço. Um não deve ocultar o outro.
    meses_medidos = MedicaoMensal.objects.values_list('mes_referencia', flat=True).distinct()
    meses_atividades = MarcoServico.objects.values_list('mes_referencia', flat=True).distinct()
    meses_metas = PlanejamentoMensal.objects.values_list('mes_referencia', flat=True).distinct()
    meses = sorted(set(meses_medidos) | set(meses_atividades) | set(meses_metas), reverse=True)
    mes = request.GET.get('mes', '')
    if mes not in meses:
        mes = meses[0] if meses else ''
    torre = request.GET.get('torre', '')
    if not torre.isdecimal() or not Torre.objects.filter(pk=int(torre)).exists():
        torre = ''
    return meses, mes, torre


def filtrar_medicoes(mes, torre):
    qs = MedicaoMensal.objects.select_related(
        'apartamento__torre', 'fvs_aprovada_por'
    )
    if mes:
        qs = qs.filter(mes_referencia=mes)
    else:
        qs = qs.none()
    if torre:
        qs = qs.filter(apartamento__torre_id=int(torre))
    return qs


def proteger_csv(valor):
    """Evita que campos de texto sejam interpretados como fórmulas pelo Excel."""
    s = '' if valor is None else str(valor)
    if s.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + s
    return s


@login_required(login_url='login_sistema')
@never_cache
def relatorios(request):
    if not request.user.is_staff:
        raise PermissionDenied('Somente equipe autorizada pode consultar relatórios internos.')
    meses, mes, torre = selecionar_filtros(request)
    medicoes = filtrar_medicoes(mes, torre)
    totais = medicoes.aggregate(
        quantidade=Count('pk'),
        avanco=Avg('percentual_concluido'),
        pendentes=Count('pk', filter=Q(status_iso='PENDENTE')),
        nao_conformes=Count('pk', filter=Q(status_iso='NAO_CONFORME')),
        concluidas=Count('pk', filter=Q(percentual_concluido=100, status_iso='CONFORME')),
    )
    por_torre = medicoes.values(
        'apartamento__torre__nome'
    ).annotate(
        quantidade=Count('pk'),
        avanco=Avg('percentual_concluido'),
        nao_conformes=Count('pk', filter=Q(status_iso='NAO_CONFORME')),
    ).order_by('apartamento__torre__nome')
    rncs_abertas = NaoConformidade.objects.exclude(situacao='RESOLVIDA')
    if mes:
        rncs_abertas = rncs_abertas.filter(medicao__mes_referencia=mes)
    if torre:
        rncs_abertas = rncs_abertas.filter(medicao__apartamento__torre_id=int(torre))
    torres_curva = Torre.objects.filter(pk=int(torre)) if torre else Torre.objects.all()
    resumo_curvas = []
    for t in torres_curva:
        curva = consolidar_curva(t)
        linha = next((linha for linha in curva['linhas'] if linha['mes'] == mes), None)
        resumo_curvas.append({'torre': t, 'pesos': curva['peso_total'],
                              'pesos_ok': curva['pesos_ok'], 'linha': linha})
    return render(request, 'obras/relatorios.html', {
        'meses': meses, 'mes': mes, 'torre_id': torre,
        'torres': Torre.objects.all(),
        'totais': totais, 'por_torre': por_torre,
        'rncs_abertas': rncs_abertas.count(),
        'rncs_atrasadas': rncs_abertas.filter(prazo__lt=timezone.localdate()).count(),
        'resumo_curvas': resumo_curvas,
    })


@login_required(login_url='login_sistema')
@never_cache
def exportar_medicoes_csv(request):
    if not request.user.is_staff:
        raise PermissionDenied('Exportação restrita à equipe autorizada.')
    _, mes, torre = selecionar_filtros(request)
    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="construct_os_medicoes.csv"'
    resp.write('\ufeff')
    escritor = csv.writer(resp, delimiter=';')
    escritor.writerow([
        'Torre', 'Apartamento', 'Andar', 'Mês', 'Etapa',
        'Avanço físico (%)', 'Situação FVS', 'Requisito', 'Aprovado por',
    ])
    for med in filtrar_medicoes(mes, torre).order_by(
            'apartamento__torre__nome', 'apartamento__andar', 'apartamento__numero'
            ).iterator(chunk_size=500):
        escritor.writerow([proteger_csv(v) for v in [
            med.apartamento.torre.nome, med.apartamento.numero,
            med.apartamento.andar, med.mes_referencia, med.etapa_atual,
            med.percentual_concluido, med.get_status_iso_display(),
            med.requisito_iso,
            med.fvs_aprovada_por.get_username() if med.fvs_aprovada_por else '',
        ]])
    return resp


@login_required(login_url='login_sistema')
@never_cache
def exportar_rncs_csv(request):
    if not request.user.is_staff:
        raise PermissionDenied('Exportação restrita à equipe autorizada.')
    _, mes, torre = selecionar_filtros(request)
    qs = NaoConformidade.objects.select_related(
        'medicao__apartamento__torre', 'responsavel', 'aberta_por',
    )
    if mes:
        qs = qs.filter(medicao__mes_referencia=mes)
    else:
        qs = qs.none()
    if torre:
        qs = qs.filter(medicao__apartamento__torre_id=int(torre))
    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="construct_os_rncs.csv"'
    resp.write('\ufeff')
    escritor = csv.writer(resp, delimiter=';')
    escritor.writerow([
        'RNC', 'Torre', 'Apartamento', 'Mês', 'Título', 'Descrição',
        'Prioridade', 'Situação', 'Ação corretiva', 'Responsável',
        'Prazo', 'Aberta por', 'Data de abertura',
    ])
    for rnc in qs.order_by('pk').iterator(chunk_size=500):
        escritor.writerow([proteger_csv(v) for v in [
            rnc.pk, rnc.medicao.apartamento.torre.nome,
            rnc.medicao.apartamento.numero, rnc.medicao.mes_referencia,
            rnc.titulo, rnc.descricao, rnc.get_prioridade_display(),
            rnc.get_situacao_display(), rnc.acao_corretiva,
            rnc.responsavel.get_username() if rnc.responsavel else '',
            rnc.prazo.isoformat() if rnc.prazo else '',
            rnc.aberta_por.get_username() if rnc.aberta_por else '',
            rnc.aberta_em.strftime('%Y-%m-%d %H:%M'),
        ]])
    return resp



@login_required(login_url='login_sistema')
@never_cache
def exportar_servicos_csv(request):
    """Exporta planejamento ponderado bruto; não inventa linhas para meses ausentes."""
    if not request.user.is_staff:
        raise PermissionDenied('Exportação restrita à equipe autorizada.')
    torre_id = request.GET.get('torre', '')
    mes = request.GET.get('mes', '')
    qs = MarcoServico.objects.select_related(
        'servico__torre', 'atualizado_por'
    )
    if torre_id.isdecimal():
        qs = qs.filter(servico__torre_id=int(torre_id))
    if mes:
        try:
            validar_mes_referencia(mes)
        except Exception:
            qs = qs.none()
        else:
            qs = qs.filter(mes_referencia=mes)
    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="construct_os_curva_s_servicos.csv"'
    resp.write('\ufeff')
    escritor = csv.writer(resp, delimiter=';')
    escritor.writerow([
        'Torre', 'Código', 'Descrição do serviço', 'Peso (%)', 'Mês',
        'Planejado acumulado do serviço (%)', 'Executado acumulado do serviço (%)',
        'Atualizado por', 'Data da atualização',
    ])
    for marco in qs.order_by('servico__torre__nome', 'servico__codigo', 'mes_referencia').iterator(chunk_size=500):
        escritor.writerow([proteger_csv(v) for v in [
            marco.servico.torre.nome, marco.servico.codigo, marco.servico.descricao,
            marco.servico.peso_percentual, marco.mes_referencia,
            marco.previsto_acumulado if marco.previsto_acumulado is not None else '',
            marco.realizado_acumulado if marco.realizado_acumulado is not None else '',
            marco.atualizado_por.get_username() if marco.atualizado_por else '',
            marco.atualizado_em.strftime('%Y-%m-%d %H:%M'),
        ]])
    return resp
