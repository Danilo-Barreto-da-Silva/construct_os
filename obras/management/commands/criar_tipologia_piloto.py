"""Gera uma tipologia INTEIRAMENTE FICTÍCIA para ensaio de QR, vídeo e pesos.

Não altera medições, FVS, RNC, cronograma ou dados reais existentes.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from obras.models import (
    Torre, Apartamento, TipologiaUnidade, AmbienteTipologia, ServicoTipologia,
    CriterioVistoria, UnidadeInteligente,
)


EXEMPLO = (
    ('ALV','Alvenaria', '25', [('LEV','Paredes levantadas','60','VISUAL'),('ENC','Encunhamento e arremates','40','MEDICAO')]),
    ('ELE','Elétrica embutida','18',[('CX','Caixas elétricas chumbadas','35','VISUAL'),('COND','Eletrodutos instalados','35','VISUAL'),('CAB','Cabos e circuitos testados','30','TESTE')]),
    ('AGU','Água fria/quente','15',[('PONTO','Pontos de água instalados','50','VISUAL'),('TEST','Teste de estanqueidade','50','TESTE')]),
    ('ESG','Esgoto e ventilação','10',[('RAMAIS','Ramais e esperas','60','VISUAL'),('TEST','Teste do sistema','40','TESTE')]),
    ('REB','Reboco','15',[('AMB','Reboco de paredes','70','VISUAL'),('PRUMO','Prumo e planeza verificados','30','MEDICAO')]),
    ('CTR','Contrapiso','10',[('EXEC','Contrapiso executado','80','VISUAL'),('NIV','Nível e caimentos medidos','20','MEDICAO')]),
    ('REV','Revestimentos','5',[('EXEC','Revestimentos instalados','70','VISUAL'),('ACAB','Qualidade e acabamento','30','DOCUMENTAL')]),
    ('PIN','Pintura','2',[('PREP','Preparação da superfície','40','VISUAL'),('FIN','Pintura final','60','VISUAL')]),
)


class Command(BaseCommand):
    help = 'Criar tipologia e critérios FICTÍCIOS na torre indicada, sem tocar em medição/FVS.'

    def add_arguments(self,parser):
        parser.add_argument('--torre-id',required=True,type=int)
        parser.add_argument('--apto-id',required=True,type=int)
        parser.add_argument('--confirmar-demo',action='store_true')

    @transaction.atomic
    def handle(self,*args,**opts):
        if not opts['confirmar_demo']:
            raise CommandError('Use --confirmar-demo para declarar que esses pesos são fictícios.')
        torre=Torre.objects.filter(pk=opts['torre_id']).first()
        apto=Apartamento.objects.filter(pk=opts['apto_id'],torre=torre).first()
        if not torre or not apto:
            raise CommandError('A torre ou o apartamento não existe, ou não pertence à torre.')
        if TipologiaUnidade.objects.filter(torre=torre,codigo='PILOTO-IA').exists():
            raise CommandError('A tipologia PILOTO-IA já existe; nenhum registro foi alterado.')
        if UnidadeInteligente.objects.filter(apartamento=apto).exists():
            raise CommandError('Apartamento já possui tipologia; não será substituída.')
        tipo=TipologiaUnidade.objects.create(
            torre=torre,codigo='PILOTO-IA',
            nome='Tipologia demonstrativa — não usar como projeto executivo',
            descricao='Critérios e pesos fictícios. Exigem revisão técnica antes de uso real.'
        )
        for codigo,nome in [('SALA','Sala de testes'),('COZ','Cozinha de testes'),('BWC','Banheiro de testes')]:
            AmbienteTipologia.objects.create(tipologia=tipo,codigo=codigo,nome=nome)
        for codigo,nome,peso,criterios in EXEMPLO:
            servico=ServicoTipologia(tipologia=tipo,codigo=codigo,nome=nome,peso=Decimal(peso))
            servico.full_clean()
            servico.save()
            for cod,desc,peso_criterio,modo in criterios:
                item=CriterioVistoria(
                    servico=servico,codigo=cod,descricao=desc,
                    peso=Decimal(peso_criterio),metodo=modo
                )
                item.full_clean()
                item.save()
        cfg=UnidadeInteligente(apartamento=apto,tipologia=tipo)
        cfg.full_clean()
        cfg.save()
        self.stdout.write(self.style.SUCCESS(
            f'Tipologia FICTÍCIA PILOTO-IA criada para {apto}; '
            f'{len(EXEMPLO)} serviços, QR {cfg.token_qr}. '
            'Nenhuma medição nem FVS foi alterada.'
        ))
