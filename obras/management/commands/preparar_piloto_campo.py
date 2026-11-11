"""Prepara um laboratório de vistorias SEM modificar torres/medições existentes.

Os pesos fazem SOMENTE parte de uma hipótese de teste. A origem das DISCIPLINAS
é inspirada por arquitetura, elétrica, água, esgoto e formas; não são extraídos
quantitativos nem medições dos PDFs reais enviados ao usuário.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from obras.catalogo_campo import AMBIENTES_CAMPO, SERVICOS_CAMPO
from obras.models import (
    Torre, Apartamento, TipologiaUnidade, AmbienteTipologia,
    ServicoTipologia, CriterioVistoria, UnidadeInteligente,
)

NOME_TORRE = "LAB — Vistoria experimental"
CODIGO_TIPO = "CAMPO-IA-V1"
APTO_NUMERO = "AMOSTRA-01"


class Command(BaseCommand):
    help = "Cria um laboratório fictício para filmagem, sem tocar em obras e FVS existentes."

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar-teste', action='store_true',
            help='Confirma que pesos são provisórios, sem valor contratual.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirmar_teste']:
            raise CommandError(
                'Use --confirmar-teste para declarar que este perfil NÃO é medição oficial.'
            )
        if Torre.objects.filter(nome=NOME_TORRE).exists():
            raise CommandError(
                'O laboratório já existe. Nada foi sobrescrito. '
                'Abra Projetos & Vistorias e selecione CAMPO-IA-V1.'
            )

        torre = Torre(nome=NOME_TORRE, total_andares=1)
        torre.full_clean()
        torre.save()
        apto = Apartamento(torre=torre, andar=1, numero=APTO_NUMERO)
        apto.full_clean()
        apto.save()
        tipologia = TipologiaUnidade(
            torre=torre, codigo=CODIGO_TIPO,
            nome="Apartamento de teste de campo — pesos provisórios",
            descricao=(
                "Perfil exploratório do processo construtivo, inspirado nas "
                "disciplinas arquitetônica, elétrica e hidrossanitária. "
                "Pesos internos HIPOTÉTICOS: ainda exigem orçamento, quantitativos, "
                "revisões de projeto e validação técnica da empresa. "
                "Não representa tipologia de empreendimento específico."
            ),
        )
        tipologia.full_clean()
        tipologia.save()
        for codigo, nome in AMBIENTES_CAMPO:
            ambiente = AmbienteTipologia(tipologia=tipologia, codigo=codigo, nome=nome)
            ambiente.full_clean()
            ambiente.save()
        for codigo, nome, peso, criterios in SERVICOS_CAMPO:
            servico = ServicoTipologia(
                tipologia=tipologia, codigo=codigo, nome=nome,
                peso=Decimal(str(peso)),
            )
            servico.full_clean()
            servico.save()
            for codigo_criterio, descricao, peso_criterio, metodo, orientacao in criterios:
                criterio = CriterioVistoria(
                    servico=servico, codigo=codigo_criterio,
                    descricao=descricao, peso=Decimal(str(peso_criterio)),
                    metodo=metodo, orientacao=orientacao,
                )
                criterio.full_clean()
                criterio.save()
        unidade = UnidadeInteligente(apartamento=apto, tipologia=tipologia)
        unidade.full_clean()
        unidade.save()
        quantidade = sum(len(item[3]) for item in SERVICOS_CAMPO)
        self.stdout.write(self.style.SUCCESS(
            f'Laboratório criado: torre ID={torre.pk}; apartamento ID={apto.pk}; '
            f'{len(SERVICOS_CAMPO)} serviços e {quantidade} critérios. '
            f'URL local: /inteligencia/unidade/{apto.pk}/ . '
            'Sem vídeos, sem PDF real e sem medições/FVS modificadas.'
        ))
