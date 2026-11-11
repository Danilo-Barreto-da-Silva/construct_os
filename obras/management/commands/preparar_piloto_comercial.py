"""Cria DUAS salas fictícias de mesma tipologia comercial para comparação de vídeo.

Nunca toca em dados de torres reais ou exemplos já cadastrados.
Não vincula nem publica os vídeos enviados na conversa e não cria medições.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from obras.catalogo_comercial import AMBIENTES_COMERCIAL, SERVICOS_COMERCIAL
from obras.models import (
    Torre, Apartamento, TipologiaUnidade, AmbienteTipologia,
    ServicoTipologia, CriterioVistoria, UnidadeInteligente,
)

NOME_LAB = "LAB — Salas comerciais"
TIPO_LAB = "COMERCIAL-COMPLETO-V1"
SALAS = ((1, "SALA-01"), (2, "SALA-02"))


class Command(BaseCommand):
    help = (
        "Cria duas salas de teste de mesma tipologia, com piso, pintura e forro. "
        "Pesos são apenas provisórios."
    )

    def add_arguments(self, parser):
        parser.add_argument('--confirmar-teste', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirmar_teste']:
            raise CommandError(
                'Informe --confirmar-teste. Este comando cria dados FICTÍCIOS '
                'e NÃO representa medição oficial.'
            )
        if Torre.objects.filter(nome=NOME_LAB).exists():
            raise CommandError(
                'O laboratório comercial já existe. Nada foi modificado. '
                'Abra Projetos & Vistorias e selecione COMERCIAL-COMPLETO-V1.'
            )

        torre = Torre(nome=NOME_LAB, total_andares=2)
        torre.full_clean()
        torre.save()
        tipo = TipologiaUnidade(
            torre=torre, codigo=TIPO_LAB,
            nome='Sala comercial com piso, pintura e forro — laboratório',
            descricao=(
                'Matriz demonstrativa para comparar dois vídeos de salas comerciais '
                'em pavimentos diferentes. Pesos ilustrativos e escopo presumido, '
                'sujeitos à conferência do memorial, projetos e quantidades reais. '
                'Hidrossanitário e esquadrias devem ser excluídos ou reponderados '
                'se não existirem no escopo da sala. NÃO usar para medição contratual.'
            ),
        )
        tipo.full_clean()
        tipo.save()

        for codigo, nome in AMBIENTES_COMERCIAL:
            ambiente = AmbienteTipologia(tipologia=tipo, codigo=codigo, nome=nome)
            ambiente.full_clean()
            ambiente.save()

        for codigo, nome, peso, criterios in SERVICOS_COMERCIAL:
            servico = ServicoTipologia(
                tipologia=tipo, codigo=codigo,
                nome=nome, peso=Decimal(str(peso)),
            )
            servico.full_clean()
            servico.save()
            for cod_criterio, descricao, peso_criterio, metodo, orientacao in criterios:
                item = CriterioVistoria(
                    servico=servico, codigo=cod_criterio,
                    descricao=descricao,
                    peso=Decimal(str(peso_criterio)),
                    metodo=metodo, orientacao=orientacao,
                )
                item.full_clean()
                item.save()

        for andar, numero in SALAS:
            sala = Apartamento(torre=torre, andar=andar, numero=numero)
            sala.full_clean()
            sala.save()
            unidade = UnidadeInteligente(apartamento=sala, tipologia=tipo)
            unidade.full_clean()
            unidade.save()
            self.stdout.write(
                f'Unidade experimental: {numero} (andar {andar}), '
                f'/inteligencia/unidade/{sala.pk}/'
            )

        self.stdout.write(
            self.style.SUCCESS(
                'Criadas duas salas da mesma tipologia COMERCIAL-COMPLETO-V1, '
                f'{len(SERVICOS_COMERCIAL)} serviços com pesos PROVISÓRIOS e '
                f'{sum(len(s[3]) for s in SERVICOS_COMERCIAL)} critérios. '
                'Nenhuma FVS, RNC ou medição anterior foi alterada.'
            )
        )
