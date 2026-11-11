"""Duas salas comerciais idênticas de projeto, com histórico de vídeo independente.

Testes usam dados sintéticos. Nenhum vídeo de obra real é utilizado aqui.
"""
from decimal import Decimal
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from .catalogo_comercial import SERVICOS_COMERCIAL
from .models import (
    Apartamento, Torre, MedicaoMensal, TipologiaUnidade, UnidadeInteligente,
    ServicoTipologia, CriterioVistoria, VistoriaInteligente, MedicaoCriterio,
)
from .parametros import progresso_unidade, validar_medicao


class PilotoComercialTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.tecnico = Usuario.objects.create_user(
            username='tecnico-comercial', password='senha-de-teste',
            is_staff=True
        )
        cls.operario = Usuario.objects.create_user(
            username='operario-comercial', password='senha-de-teste',
        )
        cls.torre_legada = Torre.objects.create(
            nome='Torre original preservada',total_andares=6
        )
        cls.apto_legado = Apartamento.objects.create(
            torre=cls.torre_legada,andar=1,numero='101'
        )
        cls.medicao_legada = MedicaoMensal.objects.create(
            apartamento=cls.apto_legado,mes_referencia='2026-11',
            percentual_concluido=42,status_iso='PENDENTE'
        )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        media = override_settings(MEDIA_ROOT=self.tmp.name)
        media.enable()
        self.addCleanup(media.disable)

    def criar_lab(self):
        call_command('preparar_piloto_comercial',confirmar_teste=True,verbosity=0)
        tipologia=TipologiaUnidade.objects.get(codigo='COMERCIAL-COMPLETO-V1')
        unidades=list(UnidadeInteligente.objects.filter(
            tipologia=tipologia
        ).select_related('apartamento').order_by('apartamento__andar'))
        return tipologia,unidades

    def test_catalogo_completo_piso_pintura_forro_e_pesos_internos(self):
        self.assertEqual(len(SERVICOS_COMERCIAL),9)
        self.assertEqual(sum(s[2] for s in SERVICOS_COMERCIAL),100)
        self.assertEqual(
            len({s[0] for s in SERVICOS_COMERCIAL}),len(SERVICOS_COMERCIAL)
        )
        self.assertTrue(all(
            sum(c[2] for c in s[3]) == 100 for s in SERVICOS_COMERCIAL
        ))
        nomes=' '.join(s[1] for s in SERVICOS_COMERCIAL).lower()
        self.assertIn('piso',nomes)
        self.assertIn('pintura',nomes)
        self.assertIn('forro',nomes)

    def test_sem_confirmacao_nao_cria_torre(self):
        with self.assertRaises(CommandError):
            call_command('preparar_piloto_comercial',verbosity=0)
        self.assertEqual(Torre.objects.count(),1)
        self.assertEqual(UnidadeInteligente.objects.count(),0)

    def test_comando_cria_duas_salas_na_mesma_tipologia_sem_tocar_legado(self):
        tipo,unidades=self.criar_lab()
        self.assertEqual(len(unidades),2)
        self.assertEqual([x.apartamento.andar for x in unidades],[1,2])
        self.assertNotEqual(unidades[0].apartamento_id,unidades[1].apartamento_id)
        self.assertEqual(unidades[0].tipologia_id,unidades[1].tipologia_id)
        self.assertEqual(
            ServicoTipologia.objects.filter(tipologia=tipo).count(),9
        )
        self.assertEqual(
            CriterioVistoria.objects.filter(servico__tipologia=tipo).count(),31
        )
        self.assertEqual(
            sum(ServicoTipologia.objects.filter(
                tipologia=tipo).values_list('peso',flat=True)),
            Decimal('100')
        )
        self.assertIsNone(progresso_unidade(unidades[0],'2026-11')['percentual'])
        self.assertIsNone(progresso_unidade(unidades[1],'2026-11')['percentual'])
        self.medicao_legada.refresh_from_db()
        self.assertEqual(self.medicao_legada.percentual_concluido,42)
        self.assertEqual(self.medicao_legada.status_iso,'PENDENTE')

    def test_segunda_execucao_nao_apaga_ou_duplica(self):
        self.criar_lab()
        with self.assertRaises(CommandError):
            call_command('preparar_piloto_comercial',confirmar_teste=True,verbosity=0)
        self.assertEqual(UnidadeInteligente.objects.count(),2)
        self.assertEqual(TipologiaUnidade.objects.count(),1)

    def test_comparacao_exige_equipe_autorizada(self):
        tipo,_=self.criar_lab()
        url=reverse('comparar_unidades_tipologia',args=[tipo.pk])
        self.assertEqual(self.client.get(url).status_code,302)
        self.client.force_login(self.operario)
        self.assertEqual(self.client.get(url).status_code,403)
        self.client.force_login(self.tecnico)
        resp=self.client.get(url)
        self.assertEqual(resp.status_code,200)
        self.assertContains(resp,'SALA-01')
        self.assertContains(resp,'SALA-02')
        self.assertContains(resp,'Indisponível')
        self.assertContains(resp,'mesma tipologia')

    def test_dashboard_lateral_mostra_salas_sem_medicao_legada(self):
        _, unidades = self.criar_lab()
        self.client.force_login(self.tecnico)
        response = self.client.get(reverse('painel_principal'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sgo-sidebar')
        self.assertContains(response, 'Painel executivo')
        self.assertContains(response, 'SALA-01')
        self.assertContains(response, 'SALA-02')
        self.assertContains(response, 'Unidades para vistoria inteligente')
        self.assertEqual(len(response.context['unidades_inteligentes']), 2)

    def test_ficha_unidade_exibe_graficos_e_cabeamento_manual(self):
        _, unidades = self.criar_lab()
        sala = unidades[0]
        self.client.force_login(self.tecnico)
        response = self.client.get(reverse('unidade_inteligente', args=[sala.apartamento_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Avanço por serviço')
        self.assertContains(response, 'Ferramentas e registros')
        self.assertContains(response, 'id="sec-gravar"')
        self.assertContains(response, 'id="sec-cabeamento"')
        self.assertContains(response, 'Aguardando informação técnica')
        self.assertContains(response, 'Indisponível')
        self.assertIsNone(response.context['progresso']['percentual'])
        self.assertEqual(response.context['cabeamento'].codigo, 'CAB')
        self.assertEqual(MedicaoCriterio.objects.count(), 0)

    def test_cabeamento_nao_vai_para_gemini_mas_pode_ser_medido_por_tecnico(self):
        _, unidades = self.criar_lab()
        sala = unidades[0]
        cabo = CriterioVistoria.objects.get(
            servico__tipologia=sala.tipologia, servico__codigo='ELE', codigo='CAB'
        )
        self.assertEqual(cabo.metodo, 'DOCUMENTAL')
        visto = VistoriaInteligente.objects.create(
            apartamento=sala.apartamento, enviado_por=self.tecnico,
            arquivo=SimpleUploadedFile('teste.mp4',
               b'\x00\x00\x00\x18ftypisom' + b'\x00'*50),
        )
        from .gemini_multimodal import preparar_contexto
        chaves, criterios, refs = preparar_contexto(visto)
        self.assertNotIn('ELE/CAB', chaves)
        self.assertNotIn('ELE/CAB', [c['chave'] for c in criterios])

        url = reverse('validar_criterio_view', args=[sala.apartamento_id])
        dados = {
            'criterio': str(cabo.pk), 'mes': '2026-11',
            'percentual': '60', 'observacao': 'Conferência documental do cabeamento.',
            'vistoria': '',
        }
        self.client.force_login(self.operario)
        self.assertEqual(self.client.post(url, dados).status_code, 403)
        self.assertFalse(MedicaoCriterio.objects.exists())
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        med = MedicaoCriterio.objects.get(
            apartamento=sala.apartamento, criterio=cabo
        )
        self.assertEqual(med.percentual_validado, Decimal('60'))
        self.assertEqual(med.validado_por, self.tecnico)
        self.assertIsNone(progresso_unidade(sala,'2026-11')['percentual'])
        self.medicao_legada.refresh_from_db()
        self.assertEqual(self.medicao_legada.percentual_concluido, 42)

    def test_videos_e_metricas_nao_se_misturam(self):
        tipo,unidades=self.criar_lab()
        primeiro,segundo=unidades
        visto1=VistoriaInteligente.objects.create(
            apartamento=primeiro.apartamento,
            enviado_por=self.tecnico,
            arquivo=SimpleUploadedFile('primeiro.mp4',b'\x00\x00\x00\x18ftypisom'+b'\x00'*50),
            estado='ANALISADA',
            resumo_ia='Primeira sala: apenas caixas elétricas aparentes.',
        )
        visto2=VistoriaInteligente.objects.create(
            apartamento=segundo.apartamento,
            enviado_por=self.tecnico,
            arquivo=SimpleUploadedFile('segundo.mp4',b'\x00\x00\x00\x18ftypisom'+b'\x00'*50),
            estado='ANALISADA',
            resumo_ia='Segunda sala: piso e forro aparentes.',
        )
        criterio=CriterioVistoria.objects.get(
            servico__tipologia=tipo,servico__codigo='ELE',codigo='CX'
        )
        validar_medicao(
            autor=self.tecnico,unidade=primeiro,criterio=criterio,
            mes='2026-11',percentual=25,
        )
        self.assertEqual(
            MedicaoCriterio.objects.filter(apartamento=primeiro.apartamento).count(),1
        )
        self.assertEqual(
            MedicaoCriterio.objects.filter(apartamento=segundo.apartamento).count(),0
        )
        self.assertIsNone(progresso_unidade(primeiro,'2026-11')['percentual'])
        self.assertIsNone(progresso_unidade(segundo,'2026-11')['percentual'])
        self.client.force_login(self.tecnico)
        resp=self.client.get(reverse('comparar_unidades_tipologia',args=[tipo.pk]),{
            'mes':'2026-11'
        })
        self.assertEqual(resp.status_code,200)
        comparados=resp.context['comparativos']
        self.assertEqual(comparados[0]['vistoria'].pk,visto1.pk)
        self.assertEqual(comparados[1]['vistoria'].pk,visto2.pk)
        self.assertContains(resp,'Primeira sala: apenas caixas elétricas aparentes.')
        self.assertContains(resp,'Segunda sala: piso e forro aparentes.')
        self.assertContains(resp,'não é uma medição contratual')
