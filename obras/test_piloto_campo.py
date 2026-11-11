"""Regressão da preparação do piloto de vídeo de obra sem dados oficiais."""
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from .catalogo_campo import SERVICOS_CAMPO
from .gemini_multimodal import RelatoMultimodal, SugestaoEstruturada, processar_vistoria
from .models import (
    Apartamento, Torre, TipologiaUnidade, ServicoTipologia, CriterioVistoria,
    UnidadeInteligente, MedicaoMensal, VistoriaInteligente, SugestaoEtapaIA,
    MedicaoCriterio, DocumentoProjeto,
)
from .parametros import progresso_unidade


class PilotoCampoTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        media = override_settings(MEDIA_ROOT=self.tmp.name)
        media.enable()
        self.addCleanup(media.disable)
        Usuario = get_user_model()
        self.gestor = Usuario.objects.create_user('gestor-campo', password='123456-TEST', is_staff=True)
        self.usuario = Usuario.objects.create_user('operador-campo', password='123456-TEST')
        self.outro = Usuario.objects.create_user('outro-campo', password='123456-TEST')
        self.torre_antiga = Torre.objects.create(nome='Torre A preservada',total_andares=6)
        self.apto_antigo = Apartamento.objects.create(
            torre=self.torre_antiga, numero='101', andar=1
        )
        self.medicao_antiga = MedicaoMensal.objects.create(
            apartamento=self.apto_antigo,mes_referencia='2026-11',
            percentual_concluido=55,status_iso='NAO_CONFORME'
        )

    def preparar(self):
        call_command('preparar_piloto_campo',confirmar_teste=True,verbosity=0)
        return UnidadeInteligente.objects.select_related('tipologia','apartamento').get(
            tipologia__codigo='CAMPO-IA-V1'
        )

    def video(self):
        return SimpleUploadedFile(
            'vistoria-campo.mp4', b'\x00\x00\x00\x18ftypisom' + b'\x00'*100,
            content_type='video/mp4',
        )

    def test_catalogo_e_pesos_internos_sao_completos(self):
        self.assertEqual(sum(s[2] for s in SERVICOS_CAMPO), 100)
        self.assertEqual(len(SERVICOS_CAMPO), 11)
        self.assertTrue(all(sum(c[2] for c in s[3]) == 100 for s in SERVICOS_CAMPO))
        codigos = [s[0] for s in SERVICOS_CAMPO]
        self.assertEqual(len(codigos),len(set(codigos)))
        self.assertTrue(any(c[3]=='TESTE' for s in SERVICOS_CAMPO for c in s[3]))
        self.assertTrue(any(c[3]=='MEDICAO' for s in SERVICOS_CAMPO for c in s[3]))

    def test_sem_confirmacao_nao_cria_nada(self):
        with self.assertRaises(CommandError):
            call_command('preparar_piloto_campo',verbosity=0)
        self.assertEqual(Torre.objects.count(),1)
        self.assertEqual(UnidadeInteligente.objects.count(),0)

    def test_cria_laboratorio_sem_sobrescrever_apartamentos_antigos(self):
        config = self.preparar()
        self.assertEqual(config.apartamento.numero,'AMOSTRA-01')
        self.assertEqual(config.apartamento.torre.nome,'LAB — Vistoria experimental')
        self.assertEqual(config.tipologia.codigo,'CAMPO-IA-V1')
        self.assertEqual(ServicoTipologia.objects.filter(tipologia=config.tipologia).count(),11)
        self.assertEqual(
            CriterioVistoria.objects.filter(servico__tipologia=config.tipologia).count(),
            sum(len(s[3]) for s in SERVICOS_CAMPO),
        )
        self.assertEqual(
            sum(ServicoTipologia.objects.filter(tipologia=config.tipologia)
                .values_list('peso',flat=True)),Decimal('100')
        )
        self.assertIsNone(progresso_unidade(config,'2026-11')['percentual'])
        self.medicao_antiga.refresh_from_db()
        self.assertEqual(self.medicao_antiga.percentual_concluido,55)
        self.assertEqual(self.medicao_antiga.status_iso,'NAO_CONFORME')
        self.assertEqual(MedicaoCriterio.objects.count(),0)

    def test_segunda_execucao_nao_duplica_nem_apaga_dados(self):
        config = self.preparar()
        with self.assertRaises(CommandError):
            call_command('preparar_piloto_campo',confirmar_teste=True,verbosity=0)
        self.assertEqual(UnidadeInteligente.objects.count(),1)
        self.assertEqual(UnidadeInteligente.objects.first().pk,config.pk)

    def test_roteiro_de_campo_e_tempo_de_gravacao_no_apartamento(self):
        cfg = self.preparar()
        self.client.force_login(self.gestor)
        resp=self.client.get(reverse('unidade_inteligente',args=[cfg.apartamento_id]))
        self.assertContains(resp,'PROTOCOLO DE CAMPO')
        self.assertContains(resp,'Duração máxima: 120 segundos')
        self.assertContains(resp,'caixas elétricas chumbadas')
        self.assertContains(resp,'Pesos')
        self.assertContains(resp,'não representam medição física real')

    def test_video_pendente_nao_atualiza_medicao_oficial(self):
        cfg = self.preparar()
        self.client.force_login(self.usuario)
        resp = self.client.post(reverse('enviar_video_inteligente',args=[cfg.apartamento_id]),{
            'arquivo':self.video(),
            'observacao':'A caixa da sala está chumbada; ainda falta teste de pressão.',
        })
        self.assertEqual(resp.status_code,302)
        item=VistoriaInteligente.objects.get(apartamento=cfg.apartamento)
        self.assertEqual(item.estado,'PENDENTE')
        self.assertFalse(MedicaoCriterio.objects.exists())
        self.medicao_antiga.refresh_from_db()
        self.assertEqual(self.medicao_antiga.percentual_concluido,55)

    def test_video_restrito_ao_autor_ou_equipe(self):
        cfg = self.preparar()
        item=VistoriaInteligente.objects.create(
            apartamento=cfg.apartamento, enviado_por=self.usuario,
            arquivo=self.video(), estado='PENDENTE',
        )
        rotas=('detalhe_vistoria_inteligente','video_privado','video_reproducao')
        self.client.force_login(self.outro)
        for nome in rotas:
            self.assertEqual(self.client.get(reverse(nome,args=[item.pk])).status_code,403)
        self.client.force_login(self.usuario)
        for nome in rotas:
            self.assertEqual(self.client.get(reverse(nome,args=[item.pk])).status_code,200)
        self.client.force_login(self.gestor)
        for nome in rotas:
            self.assertEqual(self.client.get(reverse(nome,args=[item.pk])).status_code,200)

    def test_pdf_restrito_a_equipe_tecnica(self):
        cfg = self.preparar()
        doc=DocumentoProjeto.objects.create(
            tipologia=cfg.tipologia,disciplina='ELE',nome='projeto fictício',
            arquivo=SimpleUploadedFile('planta.pdf',b'%PDF-1.4\n%%EOF'),
        )
        self.client.force_login(self.usuario)
        for nome in ('documento_privado','documento_visualizacao'):
            self.assertEqual(self.client.get(reverse(nome,args=[doc.pk])).status_code,403)
        self.client.force_login(self.gestor)
        for nome in ('documento_privado','documento_visualizacao'):
            self.assertEqual(self.client.get(reverse(nome,args=[doc.pk])).status_code,200)

    def test_ai_organiza_fato_visual_de_audio_sem_preencher_medicao(self):
        cfg=self.preparar()
        criterio=CriterioVistoria.objects.get(servico__tipologia=cfg.tipologia,servico__codigo='ELE',codigo='CX')
        video=VistoriaInteligente.objects.create(
            apartamento=cfg.apartamento,enviado_por=self.gestor,arquivo=self.video()
        )
        resposta=RelatoMultimodal(
            resumo='Uma caixa elétrica é visível e outros trechos não puderam ser verificados.',
            transcricao_narrada='As caixas estão chumbadas na sala.',
            sugestoes=[SugestaoEstruturada(
                chave='ELE/CX', fonte='AMBAS', percentual_sugerido=None,
                instante_segundos=15,
                justificativa='Apenas parte da parede apareceu.',
                evidencia_visual='Uma caixa visível na parede.',
                declaracao_audio='O narrador diz que todas estão chumbadas.',
                pendencia_verificacao='Conferir quantitativos e pontos do projeto.',
            )],
        )
        with patch('obras.gemini_multimodal._consultar_gemini',return_value=resposta):
            self.assertTrue(processar_vistoria(video.pk))
        sugestao=SugestaoEtapaIA.objects.get(vistoria=video,criterio=criterio)
        self.assertIsNone(sugestao.percentual_sugerido)
        self.assertIn('VISUAL: Uma caixa visível',sugestao.justificativa)
        self.assertIn('ÁUDIO (declaração):',sugestao.justificativa)
        self.assertIn('PENDENTE DE VERIFICAÇÃO:',sugestao.justificativa)
        self.assertFalse(MedicaoCriterio.objects.exists())
        self.medicao_antiga.refresh_from_db()
        self.assertEqual(self.medicao_antiga.status_iso,'NAO_CONFORME')
