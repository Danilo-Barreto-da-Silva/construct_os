"""Operações de qualidade com transações e registro de autoria.

Os eventos são trilha operacional interna, não assinatura digital certificada.
"""
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from .models import (
    EventoFVS, EventoRNC, HistoricoMedicao, ItemFVS,
    MedicaoMensal, NaoConformidade,
)


def registrar_status_medicao(medicao, autor, status, motivo):
    """Alteração de FVS preservando o percentual físico, com trilha de auditoria."""
    status_anterior = medicao.status_iso
    if status_anterior == status:
        return False
    medicao.status_iso = status
    medicao.fvs_aprovada_por = None
    medicao.fvs_aprovada_em = None
    medicao.full_clean()
    medicao.save(update_fields=['status_iso', 'fvs_aprovada_por', 'fvs_aprovada_em'])
    HistoricoMedicao.objects.create(
        medicao=medicao, autor=autor, origem='MANUAL',
        percentual_anterior=medicao.percentual_concluido,
        percentual_novo=medicao.percentual_concluido,
        status_anterior=status_anterior, status_novo=status,
        etapa_anterior=medicao.etapa_atual, etapa_nova=medicao.etapa_atual,
        observacao=motivo[:2000],
    )
    return True


@transaction.atomic
def abrir_rnc(medicao_id, *, autor, titulo, descricao, prioridade):
    medicao = MedicaoMensal.objects.select_for_update().get(pk=medicao_id)
    rnc = NaoConformidade(
        medicao=medicao, aberta_por=autor,
        titulo=titulo.strip(), descricao=descricao.strip(), prioridade=prioridade,
    )
    rnc.full_clean()
    rnc.save()
    EventoRNC.objects.create(
        rnc=rnc, autor=autor, situacao_anterior='',
        situacao_nova='ABERTA', descricao='RNC aberta: ' + descricao[:1000],
    )
    registrar_status_medicao(
        medicao, autor, 'NAO_CONFORME', f'RNC #{rnc.pk} aberta: {titulo}',
    )
    return rnc


@transaction.atomic
def atualizar_rnc(rnc_id, *, autor, situacao, acao_corretiva, responsavel, prazo, comentario=''):
    if not autor.is_staff:
        raise PermissionDenied('A atualização e o encerramento de RNC exigem membro autorizado.')
    rnc = NaoConformidade.objects.select_for_update().get(pk=rnc_id)
    anterior = rnc.situacao
    valores_anteriores = (rnc.situacao, rnc.acao_corretiva, rnc.responsavel_id, rnc.prazo)
    rnc.situacao = situacao
    rnc.acao_corretiva = acao_corretiva.strip()
    rnc.responsavel = responsavel
    rnc.prazo = prazo
    if situacao == 'RESOLVIDA' and anterior != 'RESOLVIDA':
        rnc.encerrada_por = autor
        rnc.encerrada_em = timezone.now()
    elif situacao != 'RESOLVIDA':
        rnc.encerrada_por = None
        rnc.encerrada_em = None
    rnc.full_clean()
    rnc.save()
    alterou = valores_anteriores != (
        rnc.situacao, rnc.acao_corretiva, rnc.responsavel_id, rnc.prazo
    )
    if alterou or comentario.strip():
        EventoRNC.objects.create(
            rnc=rnc, autor=autor, situacao_anterior=anterior,
            situacao_nova=situacao,
            descricao=(comentario.strip() or
                       f'Situação: {anterior} → {situacao}. Ação e atribuição atualizadas.')[:2000],
        )
    # Uma RNC resolvida exige reavaliação própria da FVS:
    # NÃO converte automaticamente a medição para CONFORME.
    return rnc


@transaction.atomic
def salvar_item_fvs(medicao_id, *, autor, descricao, resultado, observacao, item_id=None):
    if resultado in ('CONFORME', 'NA') and not autor.is_staff:
        raise PermissionDenied('Somente equipe autorizada pode confirmar um item de FVS.')
    medicao = MedicaoMensal.objects.select_for_update().get(pk=medicao_id)
    if item_id is not None:
        item = ItemFVS.objects.select_for_update().get(pk=item_id, medicao_id=medicao_id)
        resultado_anterior = item.resultado
        valores_anteriores = (item.descricao, item.resultado, item.observacao)
    else:
        item = ItemFVS(medicao=medicao)
        resultado_anterior = ''
        valores_anteriores = None

    item.descricao = descricao.strip()
    item.resultado = resultado
    item.observacao = observacao.strip()
    item.verificado_por = autor
    item.full_clean()
    item.save()

    valores_novos = (item.descricao, item.resultado, item.observacao)
    if valores_anteriores != valores_novos:
        EventoFVS.objects.create(
            item=item, autor=autor,
            resultado_anterior=resultado_anterior,
            resultado_novo=resultado,
            observacao=f'{descricao[:180]}: {observacao[:850]}',
        )
        if medicao.status_iso == 'CONFORME':
            registrar_status_medicao(
                medicao, autor, 'PENDENTE',
                'Checklist FVS alterado após aprovação. Necessária nova revisão.',
            )
    return item
