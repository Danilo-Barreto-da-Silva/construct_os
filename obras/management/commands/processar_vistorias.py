"""Processa vídeos pendentes fora do HTTP; exige API configurada e comando explícito."""
import logging
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from obras.models import VistoriaInteligente
from obras.gemini_multimodal import processar_vistoria


log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Processar até N vídeos pendentes com Gemini (com custo de API).'

    def add_arguments(self, parser):
        parser.add_argument('--limite', type=int, default=1)

    def handle(self, *args, **opts):
        limite = opts['limite']
        if not (1 <= limite <= 10):
            raise CommandError('Informe --limite entre 1 e 10.')
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == 'MODO_SIMULACAO':
            raise CommandError('GEMINI_API_KEY não configurada. Nenhum arquivo processado.')
        ids = list(
            VistoriaInteligente.objects.filter(estado='PENDENTE')
            .order_by('criado_em').values_list('pk',flat=True)[:limite]
        )
        feitos=0
        falhas=0
        for pk in ids:
            try:
                if processar_vistoria(pk):
                    feitos+=1
            except Exception:
                falhas+=1
                log.exception('Falha processando vistoria id=%s',pk)
        self.stdout.write(
            self.style.SUCCESS(f'Processadas: {feitos}; falhas: {falhas}; selecionadas: {len(ids)}.')
        )
