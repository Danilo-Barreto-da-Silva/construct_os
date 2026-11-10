"""Testes dos relatórios, exportações e proteções operacionais."""
from unittest.mock import patch
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    Apartamento, ItemFVS, MedicaoMensal, NaoConformidade,
    PlanejamentoMensal, EventoPlanejamento, Torre,
)


class RelatoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff = User.objects.create_user(
            'gestor-rel', password='testes-seguros', is_staff=True,
        )
        cls.auxiliar = User.objects.create_user(
            'auxiliar-rel', password='testes-seguros',
        )
        cls.torre = Torre.objects.create(nome='Torre =A', total_andares=4)
        cls.apto = Apartamento.objects.create(torre=cls.torre, andar=2, numero='201')
        cls.medicao = MedicaoMensal.objects.create(
            apartamento=cls.apto, mes_referencia='2026-11',
            percentual_concluido=65, status_iso='PENDENTE',
            etapa_atual='=SOMAR(1;1)',
        )

    def test_relatorio_exige_staff(self):
        self.assertEqual(self.client.get(reverse('relatorios')).status_code, 302)
        self.client.force_login(self.auxiliar)
        for nome in ('relatorios', 'exportar_medicoes_csv', 'exportar_rncs_csv'):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 403)

    def test_relatorio_exibe_numeros_cadastrados(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('relatorios'), {'mes': '2026-11'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['totais']['quantidade'], 1)
        self.assertEqual(resp.context['totais']['pendentes'], 1)
        self.assertAlmostEqual(resp.context['totais']['avanco'], 65)

    def test_exportacao_csv_neutraliza_formulas(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('exportar_medicoes_csv'), {'mes': '2026-11'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/csv', resp['Content-Type'])
        conteudo = resp.content.decode('utf-8-sig')
        self.assertIn("'=SOMAR(1;1)", conteudo)
        self.assertIn('Torre =A', conteudo)

    def test_rnc_csv_exporta_registros_formais(self):
        NaoConformidade.objects.create(
            medicao=self.medicao, titulo='=EVAL(1)', descricao='Falha',
            prioridade='ALTA', aberta_por=self.staff,
        )
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('exportar_rncs_csv'), {'mes': '2026-11'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("'=EVAL(1)", resp.content.decode('utf-8-sig'))

    def test_meta_incompleta_nao_gera_media_geral_inventada(self):
        torre2 = Torre.objects.create(nome='Torre B', total_andares=2)
        apto2 = Apartamento.objects.create(torre=torre2, andar=1, numero='101')
        MedicaoMensal.objects.create(
            apartamento=apto2, mes_referencia='2026-11', percentual_concluido=35,
        )
        PlanejamentoMensal.objects.create(
            torre=self.torre, mes_referencia='2026-11',
            percentual_planejado=70,
        )
        self.client.force_login(self.staff)
        painel = self.client.get(reverse('painel_principal'), {'mes': '2026-11'})
        self.assertEqual(painel.context['metas_grafico'], [None])
        PlanejamentoMensal.objects.create(
            torre=torre2, mes_referencia='2026-11',
            percentual_planejado=60,
        )
        painel = self.client.get(reverse('painel_principal'), {'mes': '2026-11'})
        self.assertEqual(painel.context['metas_grafico'], [65.0])

    def test_item_ja_criado_so_staff_pode_editar(self):
        item = ItemFVS.objects.create(
            medicao=self.medicao, descricao='Verificar esquadro', resultado='PENDENTE',
        )
        self.client.force_login(self.auxiliar)
        resp = self.client.post(
            reverse('editar_item_fvs', args=[self.medicao.pk, item.pk]), {
                'descricao': 'Tentativa indevida',
                'resultado': 'PENDENTE',
            },
        )
        self.assertEqual(resp.status_code, 403)
        item.refresh_from_db()
        self.assertEqual(item.descricao, 'Verificar esquadro')

    def test_caminho_ia_legado_recusa_upload_sem_criar_sugestao(self):
        self.client.force_login(self.staff)
        payload = SimpleUploadedFile(
            'exploit.exe', b'fake', content_type='application/octet-stream',
        )
        resp = self.client.post(
            reverse('avaliar_apartamento', args=[self.medicao.pk]),
            {'acao': 'ia_video', 'video_vistoria': payload}, follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'O envio de vídeo foi transferido')
        self.medicao.refresh_from_db()
        self.assertEqual(self.medicao.sugestao_ia, '')
        self.assertEqual(self.medicao.status_iso, 'PENDENTE')


    def test_arquivo_que_nao_e_video_e_bloqueado(self):
        self.client.force_login(self.staff)
        payload = SimpleUploadedFile(
            'exploit.exe', b'fake', content_type='application/octet-stream',
        )
        with patch('obras.views.analisar_video_obra') as analisar:
            resp = self.client.post(
                reverse('avaliar_apartamento', args=[self.medicao.pk]),
                {'acao': 'ia_video', 'video_vistoria': payload},
            )
        self.assertEqual(resp.status_code, 302)
        analisar.assert_not_called()

    def test_meta_registra_historico_de_revisoes(self):
        self.client.force_login(self.staff)
        url = reverse('planejamento')
        dados = {
            'torre': str(self.torre.pk), 'mes_referencia': '2026-11',
            'percentual_planejado': '62.50',
        }
        self.client.post(url, dados)
        dados['percentual_planejado'] = '70'
        self.client.post(url, dados)
        self.assertEqual(EventoPlanejamento.objects.count(), 2)
        eventos = list(EventoPlanejamento.objects.order_by('registrado_em', 'pk'))
        self.assertIsNone(eventos[0].percentual_anterior)
        self.assertEqual(float(eventos[1].percentual_anterior), 62.5)
        self.assertEqual(float(eventos[1].percentual_novo), 70.0)
        self.assertEqual(eventos[1].autor, self.staff)

    def test_rnc_em_atraso_aparece_no_relatorio(self):
        from datetime import timedelta
        from django.utils import timezone
        rnc = NaoConformidade.objects.create(
            medicao=self.medicao, titulo='Prazo vencido',
            descricao='Ação ainda pendente', prazo=timezone.localdate() - timedelta(days=1),
            prioridade='ALTA', aberta_por=self.staff,
        )
        self.assertTrue(rnc.em_atraso)
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('relatorios'), {'mes': '2026-11'})
        self.assertEqual(resp.context['rncs_atrasadas'], 1)
        rnc.situacao = 'RESOLVIDA'
        rnc.acao_corretiva = 'Ação concluída'
        rnc.save()
        self.assertFalse(rnc.em_atraso)

    def test_rnc_aberta_nao_pode_ser_ocultada_mudando_para_pendente(self):
        NaoConformidade.objects.create(
            medicao=self.medicao, titulo='Problema em aberto',
            descricao='Falha identificada', aberta_por=self.auxiliar,
        )
        self.medicao.status_iso = 'NAO_CONFORME'
        self.medicao.save()
        self.client.force_login(self.auxiliar)
        resp = self.client.post(reverse('avaliar_apartamento', args=[self.medicao.pk]), {
            'acao': 'manual', 'percentual': '80', 'status_iso': 'PENDENTE',
            'etapa_atual': 'Revisão',
        })
        self.assertEqual(resp.status_code, 302)
        self.medicao.refresh_from_db()
        self.assertEqual(self.medicao.status_iso, 'NAO_CONFORME')
        self.assertEqual(self.medicao.percentual_concluido, 65)

    def test_meses_parciais_nao_projetam_prazo_ou_meta(self):
        # Outubro e novembro mediram apenas 1 dos 2 apartamentos cadastrados.
        Apartamento.objects.create(torre=self.torre, andar=2, numero='202')
        MedicaoMensal.objects.create(
            apartamento=self.apto, mes_referencia='2026-10',
            percentual_concluido=40,
        )
        PlanejamentoMensal.objects.create(
            torre=self.torre, mes_referencia='2026-11',
            percentual_planejado=80,
        )
        self.client.force_login(self.staff)
        painel = self.client.get(reverse('painel_principal'), {'mes': '2026-11'})
        self.assertEqual(painel.status_code, 200)
        self.assertEqual(painel.context['total_med'], 1)
        self.assertEqual(painel.context['total_unidades'], 2)
        self.assertFalse(painel.context['cobertura_completa'])
        self.assertIsNone(painel.context['ritmo_mensal'])
        self.assertIsNone(painel.context['meses_para_terminar'])
        self.assertEqual(painel.context['metas_grafico'][-1], None)
        self.assertContains(painel, 'Cobertura incompleta')

    def test_fvs_conforme_com_zero_execucao_aparece_no_contador_de_qualidade(self):
        """Aprovar FVS não implica concluir fisicamente a medição."""
        self.medicao.status_iso = 'CONFORME'
        self.medicao.percentual_concluido = 0
        self.medicao.save(update_fields=['status_iso', 'percentual_concluido'])
        self.client.force_login(self.staff)
        painel = self.client.get(reverse('painel_principal'), {'mes': '2026-11'})
        self.assertEqual(painel.status_code, 200)
        self.assertEqual(painel.context['fvs_conformes'], 1)
        self.assertEqual(painel.context['unidades_iso_ok'], 0)
        self.assertContains(painel, 'FVS conforme')
        self.assertContains(painel, 'Concluídas fisicamente (100%)')

    def test_historico_informa_cobertura_de_cada_mes(self):
        """Uma medição isolada não deve se confundir com o avanço da obra toda."""
        from .models import Torre
        torre_nova = Torre.objects.create(nome='Torre de dezembro', total_andares=1)
        apto_novo = Apartamento.objects.create(torre=torre_nova, andar=1, numero='101')
        MedicaoMensal.objects.create(
            apartamento=apto_novo, mes_referencia='2026-12',
            percentual_concluido=0, status_iso='CONFORME',
        )
        self.client.force_login(self.staff)
        painel = self.client.get(reverse('painel_principal'), {'mes': '2026-12'})
        amostras = {x['mes']: x for x in painel.context['cobertura_grafico']}
        self.assertEqual(amostras['2026-11']['quantidade'], 1)
        self.assertEqual(amostras['2026-12']['quantidade'], 1)
        self.assertEqual(amostras['2026-12']['total'], 2)
        self.assertFalse(painel.context['cobertura_completa'])
        self.assertContains(painel, '2026-12: 1 de 2 unidades')
        self.assertContains(painel, 'Os pontos não são ligados')

    def test_relatorio_permite_filtrar_mes_com_apenas_meta_simples(self):
        PlanejamentoMensal.objects.create(
            torre=self.torre, mes_referencia='2027-01', percentual_planejado=Decimal('15'),
        )
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('relatorios'), {'mes': '2027-01'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['mes'], '2027-01')
        self.assertEqual(resp.context['totais']['quantidade'], 0)
