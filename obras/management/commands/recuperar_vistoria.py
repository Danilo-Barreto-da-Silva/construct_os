"""Inspeciona e destrava MANUALMENTE vistorias cujo processo terminou abruptamente.

Não faz upload, não chama Gemini, não reenvia vídeo nem reinicia análise.
Antes de destravar, o operador deve garantir que o worker anterior já encerrou.
"""
import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from obras.models import VistoriaInteligente


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Inspecionar vistorias PROCESSANDO e marcar uma vistoria interrompida '
        'como ERRO mediante confirmação explícita. Não reenvia ao Gemini.'
    )

    def add_arguments(self, parser):
        grupo = parser.add_mutually_exclusive_group(required=True)
        grupo.add_argument(
            '--listar', action='store_true',
            help='Listar vistorias PROCESSANDO, sem alterar o banco.'
        )
        grupo.add_argument(
            '--vistoria-id', type=int,
            help='ID específico de uma vistoria interrompida.'
        )
        parser.add_argument(
            '--confirmar', action='store_true',
            help='Confirma que o processador anterior terminou e permite marcar ERRO.'
        )

    def handle(self, *args, **opts):
        if opts['listar']:
            if opts['confirmar']:
                raise CommandError('--confirmar é exclusivo de --vistoria-id.')
            encontrados = VistoriaInteligente.objects.filter(
                estado='PROCESSANDO'
            ).order_by('criado_em', 'pk')
            total = encontrados.count()
            self.stdout.write(f'Vistorias em processamento: {total}')
            for visto in encontrados[:50]:
                self.stdout.write(
                    f'#{visto.pk}: criado em {visto.criado_em:%Y-%m-%d %H:%M %Z}; '
                    'início efetivo não registrado'
                )
            if total > 50:
                self.stdout.write('Listagem limitada aos 50 registros mais antigos.')
            self.stdout.write(
                'ATENÇÃO: confirme que não existe um processador ativo antes de '
                'destravar manualmente.'
            )
            return

        pk = opts['vistoria_id']
        if pk is None or pk < 1:
            raise CommandError('Informe um ID de vistoria válido.')
        if not opts['confirmar']:
            raise CommandError(
                'Nada alterado. Confirme que o processo anterior terminou '
                'e repita incluindo --confirmar.'
            )
        with transaction.atomic():
            visto = VistoriaInteligente.objects.select_for_update().filter(
                pk=pk
            ).first()
            if visto is None:
                raise CommandError(f'Vistoria #{pk} não encontrada.')
            if visto.estado != 'PROCESSANDO':
                raise CommandError(
                    f'Vistoria #{pk} está em {visto.estado}; nenhum registro alterado.'
                )
            if visto.sugestoes.exists():
                raise CommandError(
                    f'Vistoria #{pk} já tem sugestões vinculadas. '
                    'Requer análise técnica antes de modificar o estado.'
                )
            visto.estado = 'ERRO'
            visto.erro_publico = (
                'Processamento interrompido. Um responsável deve verificar '
                'a execução anterior antes de solicitar nova análise.'
            )
            visto.processado_em = timezone.now()
            visto.save(update_fields=['estado', 'erro_publico', 'processado_em'])
        logger.warning('Destravamento manual confirmado da vistoria id=%s', pk)
        self.stdout.write(
            self.style.SUCCESS(
                f'Vistoria #{pk} marcada como ERRO, sem reenviar o vídeo ao Google.'
            )
        )
