"""Planejamento físico ponderado independente das medições por apartamento.

Cada serviço possui peso imutável após o primeiro lançamento. Percentuais são
ACUMULADOS ao fim de cada mês; mês sem dado não equivale a 0% de avanço.
A curva só exibe resultado consolidado se os pesos somarem exatamente 100% e
todos os serviços tiverem valor naquele mês. Não é um cronograma financeiro.
"""
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import EventoMarcoServico, EventoServicoObra, MarcoServico, ServicoObra, Torre


CENTO = Decimal('100')
ZERO = Decimal('0')
CASAS = Decimal('0.01')


@transaction.atomic
def cadastrar_servico(*, autor, torre, codigo, descricao, peso_percentual):
    if not autor.is_staff:
        raise PermissionDenied('Cadastrar serviços exige autorização administrativa.')
    torre = Torre.objects.select_for_update().get(pk=torre.pk)
    servico = ServicoObra(
        torre=torre, codigo=codigo.strip(), descricao=descricao.strip(),
        peso_percentual=peso_percentual, criado_por=autor,
    )
    servico.full_clean()
    servico.save()
    return servico



@transaction.atomic
def atualizar_servico(*, autor, servico_id, descricao, peso_percentual):
    """Corrige descrição/peso com auditoria, vedando reponderar dados históricos."""
    if not autor.is_staff:
        raise PermissionDenied('Alterar serviços exige autorização administrativa.')
    # Lock da torre padroniza a verificação da soma dos pesos de serviços.
    servico_atual = ServicoObra.objects.get(pk=servico_id)
    Torre.objects.select_for_update().get(pk=servico_atual.torre_id)
    servico = ServicoObra.objects.select_for_update().get(pk=servico_id)
    anterior_descricao = servico.descricao
    anterior_peso = servico.peso_percentual
    servico.descricao = descricao.strip()
    servico.peso_percentual = peso_percentual
    servico.full_clean()
    if (servico.descricao, servico.peso_percentual) == (
        anterior_descricao, anterior_peso
    ):
        return servico, False
    servico.save(update_fields=['descricao', 'peso_percentual'])
    EventoServicoObra.objects.create(
        servico=servico, autor=autor,
        descricao_anterior=anterior_descricao, descricao_nova=servico.descricao,
        peso_anterior=anterior_peso, peso_novo=servico.peso_percentual,
    )
    return servico, True

def _validar_sequencia(servico, mes, campo, valor):
    """Percentual acumulado não pode retroceder nem ultrapassar mês posterior."""
    if valor is None:
        return
    anteriores = MarcoServico.objects.filter(
        servico=servico, mes_referencia__lt=mes,
        **{campo + '__isnull': False},
    ).order_by('-mes_referencia')
    posteriores = MarcoServico.objects.filter(
        servico=servico, mes_referencia__gt=mes,
        **{campo + '__isnull': False},
    ).order_by('mes_referencia')
    anterior = anteriores.first()
    posterior = posteriores.first()
    if anterior and valor < getattr(anterior, campo):
        raise ValidationError(
            f'O acumulado de {mes} ({valor}%) não pode ser inferior ao de '
            f'{anterior.mes_referencia} ({getattr(anterior, campo)}%).'
        )
    if posterior and valor > getattr(posterior, campo):
        raise ValidationError(
            f'O acumulado de {mes} ({valor}%) não pode superar o de '
            f'{posterior.mes_referencia} ({getattr(posterior, campo)}%).'
        )


@transaction.atomic
def registrar_marco(*, autor, servico, mes_referencia,
                    previsto_acumulado=None, realizado_acumulado=None,
                    observacao=''):
    if not autor.is_staff:
        raise PermissionDenied('Registrar progresso exige autorização administrativa.')
    servico = ServicoObra.objects.select_for_update().get(pk=servico.pk)
    existente = MarcoServico.objects.select_for_update().filter(
        servico=servico, mes_referencia=mes_referencia
    ).first()

    # Campo em branco não sobrescreve o outro acumulado já salvo.
    anterior_previsto = existente.previsto_acumulado if existente else None
    anterior_realizado = existente.realizado_acumulado if existente else None
    novo_previsto = (
        previsto_acumulado if previsto_acumulado is not None else anterior_previsto
    )
    novo_realizado = (
        realizado_acumulado if realizado_acumulado is not None else anterior_realizado
    )

    marco = existente or MarcoServico(servico=servico, mes_referencia=mes_referencia)
    marco.previsto_acumulado = novo_previsto
    marco.realizado_acumulado = novo_realizado
    marco.atualizado_por = autor
    marco.full_clean()

    _validar_sequencia(servico, mes_referencia, 'previsto_acumulado', novo_previsto)
    _validar_sequencia(servico, mes_referencia, 'realizado_acumulado', novo_realizado)

    if existente and (anterior_previsto, anterior_realizado) == (
        novo_previsto, novo_realizado
    ):
        return marco, False

    marco.save()
    EventoMarcoServico.objects.create(
        marco=marco, autor=autor,
        previsto_anterior=anterior_previsto, previsto_novo=novo_previsto,
        realizado_anterior=anterior_realizado, realizado_novo=novo_realizado,
        observacao=observacao.strip()[:1000],
    )
    return marco, True


def consolidar_curva(torre):
    """Retorna série ponderada, mantendo ausências como None, nunca como zero."""
    servicos = list(
        ServicoObra.objects.filter(torre=torre)
        .prefetch_related('marcos', 'revisoes__autor').order_by('codigo')
    )
    pesos_total = sum((servico.peso_percentual for servico in servicos), ZERO)
    pesos_ok = bool(servicos) and pesos_total == CENTO
    meses_registrados = sorted({
        marco.mes_referencia for servico in servicos
        for marco in servico.marcos.all()
    })
    # Completa o eixo temporal, mas NÃO preenche percentuais de meses
    # inexistentes. Um buraco em novembro não vira progresso artificial.
    meses = []
    if meses_registrados:
        ano_inicio, mes_inicio = map(int, meses_registrados[0].split('-'))
        ano_fim, mes_fim = map(int, meses_registrados[-1].split('-'))
        indice_inicio = ano_inicio * 12 + mes_inicio - 1
        indice_fim = ano_fim * 12 + mes_fim - 1
        # Evita carregar até cem anos de meses num erro de cadastro.
        indice_inicio = max(indice_inicio, indice_fim - 119)
        meses = [
            f'{indice // 12}-{(indice % 12) + 1:02d}'
            for indice in range(indice_inicio, indice_fim + 1)
        ]
    index = {
        servico.pk: {marco.mes_referencia: marco for marco in servico.marcos.all()}
        for servico in servicos
    }
    linhas = []
    for mes in meses:
        pontos = [index[servico.pk].get(mes) for servico in servicos]
        n_previsto = sum(
            1 for marco in pontos if marco is not None and marco.previsto_acumulado is not None
        )
        n_realizado = sum(
            1 for marco in pontos if marco is not None and marco.realizado_acumulado is not None
        )
        previsto = realizado = None
        if pesos_ok and n_previsto == len(servicos):
            previsto = sum(
                servico.peso_percentual * marco.previsto_acumulado / CENTO
                for servico, marco in zip(servicos, pontos)
            ).quantize(CASAS)
        if pesos_ok and n_realizado == len(servicos):
            realizado = sum(
                servico.peso_percentual * marco.realizado_acumulado / CENTO
                for servico, marco in zip(servicos, pontos)
            ).quantize(CASAS)
        linhas.append({
            'mes': mes,
            'previsto': previsto,
            'realizado': realizado,
            'desvio': realizado - previsto if previsto is not None and realizado is not None else None,
            'n_previsto': n_previsto, 'n_realizado': n_realizado,
            'n_servicos': len(servicos),
        })
    return {
        'servicos': servicos, 'peso_total': pesos_total, 'pesos_ok': pesos_ok,
        'meses': meses, 'linhas': linhas,
        'previstos': [float(linha['previsto']) if linha['previsto'] is not None else None for linha in linhas],
        'realizados': [float(linha['realizado']) if linha['realizado'] is not None else None for linha in linhas],
        'ultima_linha_completa': next(
            (linha for linha in reversed(linhas) if linha['desvio'] is not None), None
        ),
    }
