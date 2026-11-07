"""Regras do levantamento parametrizado por unidade.

A IA não certifica serviços, não altera FVS nem a medição mensal antiga.
Sem pesos completos ou critérios verificados: a média é INDISPONÍVEL.
"""
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from .models import (
    UnidadeInteligente, ServicoTipologia, CriterioVistoria,
    PesoServicoUnidade, MedicaoCriterio, EventoMedicaoCriterio,
    validar_mes_referencia,
)

CEM = Decimal('100')
CASAS = Decimal('0.01')


def pesos_vigentes(unidade):
    servicos = list(unidade.tipologia.servicos.prefetch_related('criterios'))
    personalizados = {
        item.servico_id: item.peso for item in unidade.pesos_proprios.all()
    }
    if personalizados:
        # Não misturar silenciosamente pesos personalizados e herdados.
        completo = len(personalizados) == len(servicos) and all(
            servico.pk in personalizados for servico in servicos
        )
        pesos = personalizados
    else:
        completo = bool(servicos)
        pesos = {servico.pk: servico.peso for servico in servicos}
    total = sum(pesos.values(), Decimal('0'))
    pesos_ok = completo and total == CEM
    criterios_ok = bool(servicos) and all(
        sum((c.peso for c in servico.criterios.all()), Decimal('0')) == CEM
        and bool(servico.criterios.all())
        for servico in servicos
    )
    return servicos, pesos, pesos_ok, criterios_ok


def progresso_unidade(unidade, mes_referencia):
    """Percentual cumulativo ponderado por serviço e subetapa confirmado até o mês.

    Nunca deduz progresso a partir de vídeo ou áudio sem confirmação humana.
    Um subitem sem medição validada permanece desconhecido (None).
    """
    validar_mes_referencia(mes_referencia)
    servicos, pesos, pesos_ok, criterios_ok = pesos_vigentes(unidade)
    medidas = MedicaoCriterio.objects.filter(
        apartamento=unidade.apartamento, mes_referencia__lte=mes_referencia
    ).order_by('criterio_id', '-mes_referencia', '-pk')
    ultimas = {}
    for med in medidas:
        ultimas.setdefault(med.criterio_id, med.percentual_validado)
    linhas = []
    total = Decimal('0')
    for servico in servicos:
        criterios = list(servico.criterios.all())
        faltantes = [crit for crit in criterios if crit.pk not in ultimas]
        parcial = None
        if criterios and not faltantes and sum((c.peso for c in criterios), Decimal('0')) == CEM:
            parcial = sum(
                (crit.peso * ultimas[crit.pk] / CEM for crit in criterios),
                Decimal('0'),
            ).quantize(CASAS)
            total += (parcial * pesos.get(servico.pk, Decimal('0')) / CEM)
        linhas.append({
            'servico': servico, 'peso': pesos.get(servico.pk), 'progresso': parcial,
            'n_criterios': len(criterios), 'n_validados': len(criterios) - len(faltantes),
        })
    completo = pesos_ok and criterios_ok and bool(linhas) and all(
        linha['progresso'] is not None for linha in linhas
    )
    return {
        'linhas': linhas, 'peso_total': sum(pesos.values(), Decimal('0')),
        'pesos_ok': pesos_ok, 'criterios_ok': criterios_ok,
        'percentual': total.quantize(CASAS) if completo else None,
        'n_criterios': sum(l['n_criterios'] for l in linhas),
        'n_validados': sum(l['n_validados'] for l in linhas),
        'mes': mes_referencia,
    }


@transaction.atomic
def validar_medicao(*, autor, unidade, criterio, mes, percentual,
                    observacao='', vistoria=None):
    if not autor.is_staff:
        raise PermissionDenied('Confirmação de medição exige autorização da equipe técnica.')
    validar_mes_referencia(mes)
    if criterio.servico.tipologia_id != unidade.tipologia_id:
        raise ValidationError('O critério não pertence à tipologia da unidade.')
    if vistoria and vistoria.apartamento_id != unidade.apartamento_id:
        raise ValidationError('A vistoria informada pertence a outra unidade.')
    if not unidade.ativo:
        raise ValidationError('Unidade não habilitada para vistorias.')
    percentual = Decimal(str(percentual))
    if not percentual.is_finite() or percentual < 0 or percentual > 100:
        raise ValidationError('Percentual deve estar entre 0% e 100%.')
    # Travar a unidade também serializa gravações em bancos com row locking.
    UnidadeInteligente.objects.select_for_update().get(pk=unidade.pk)
    anterior_mes = MedicaoCriterio.objects.filter(
        apartamento=unidade.apartamento, criterio=criterio,
        mes_referencia__lt=mes,
    ).order_by('-mes_referencia').first()
    seguinte = MedicaoCriterio.objects.filter(
        apartamento=unidade.apartamento, criterio=criterio,
        mes_referencia__gt=mes,
    ).order_by('mes_referencia').first()
    if anterior_mes and percentual < anterior_mes.percentual_validado:
        raise ValidationError('O percentual acumulado é inferior ao mês anterior.')
    if seguinte and percentual > seguinte.percentual_validado:
        raise ValidationError('O percentual acumulado excede um mês posterior.')
    medicao = MedicaoCriterio.objects.select_for_update().filter(
        apartamento=unidade.apartamento, criterio=criterio, mes_referencia=mes
    ).first()
    anterior = medicao.percentual_validado if medicao else None
    if medicao and anterior == percentual:
        return medicao, False
    medicao = medicao or MedicaoCriterio(
        apartamento=unidade.apartamento, criterio=criterio, mes_referencia=mes,
    )
    medicao.percentual_validado = percentual
    medicao.vistoria_origem = vistoria
    medicao.validado_por = autor
    medicao.full_clean()
    medicao.save()
    EventoMedicaoCriterio.objects.create(
        medicao=medicao, autor=autor, anterior=anterior,
        novo=percentual, observacao=observacao.strip()[:500],
    )
    return medicao, True
