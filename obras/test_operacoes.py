"""Testes de integração do fluxo operacional de RNC, FVS, metas e cadastros."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    Apartamento, EventoFVS, EventoRNC, HistoricoMedicao, ItemFVS,
    MedicaoMensal, NaoConformidade, PlanejamentoMensal, Torre,
)


class OperacoesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.tecnico = Usuario.objects.create_user(
            'tecnico', password='senha-de-teste', is_staff=True,
        )
        cls.auxiliar = Usuario.objects.create_user('auxiliar-op', password='senha-de-teste')
        cls.torre = Torre.objects.create(nome='Torre de testes', total_andares=6)
        cls.apto = Apartamento.objects.create(torre=cls.torre, andar=1, numero='101')
        cls.medicao = MedicaoMensal.objects.create(
            apartamento=cls.apto, mes_referencia='2026-11',
            percentual_concluido=45, etapa_atual='Alvenaria', status_iso='PENDENTE',
        )

    def postar_rnc(self):
        return self.client.post(
            reverse('abrir_rnc_pagina', args=[self.medicao.pk]),
            {
                'titulo': 'Falta de verga',
                'descricao': 'Ausência de verga na janela, conferir projeto.',
                'prioridade': 'ALTA',
            }
        )

    def test_paginas_operacionais_exigem_login(self):
        for url in [
            reverse('lista_rncs'),
            reverse('planejamento'),
            reverse('checklist_fvs', args=[self.medicao.pk]),
            reverse('abrir_rnc_pagina', args=[self.medicao.pk]),
        ]:
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_abertura_rnc_marca_nao_conformidade_e_audita(self):
        self.client.force_login(self.auxiliar)
        response = self.postar_rnc()
        self.assertEqual(response.status_code, 302)
        rnc = NaoConformidade.objects.get()
        self.assertEqual(rnc.aberta_por, self.auxiliar)
        self.assertEqual(rnc.prioridade, 'ALTA')
        self.assertEqual(rnc.situacao, 'ABERTA')
        self.medicao.refresh_from_db()
        self.assertEqual(self.medicao.percentual_concluido, 45)
        self.assertEqual(self.medicao.status_iso, 'NAO_CONFORME')
        self.assertEqual(EventoRNC.objects.count(), 1)
        self.assertEqual(HistoricoMedicao.objects.count(), 1)
        pagina = self.client.get(reverse('lista_rncs'))
        self.assertContains(pagina, 'Falta de verga')

    def test_abrir_rnc_por_auxiliar_revoga_fvs_aprovada_sem_mudar_progresso(self):
        # Regra intencional: qualquer usuário autenticado pode comunicar falha,
        # mesmo após aprovação da FVS. O histórico deve mostrar a revogação.
        self.client.force_login(self.tecnico)
        ItemFVS.objects.create(
            medicao=self.medicao, descricao='Inspeção anterior da unidade',
            resultado='CONFORME', verificado_por=self.tecnico,
        )
        resposta = self.client.post(
            reverse('avaliar_apartamento', args=[self.medicao.pk]), {
                'acao': 'manual', 'percentual': '45',
                'status_iso': 'CONFORME',
                'etapa_atual': 'Inspeção geral finalizada',
            }
        )
        self.assertEqual(resposta.status_code, 302)
        self.medicao.refresh_from_db()
        self.assertEqual(self.medicao.status_iso, 'CONFORME')
        self.assertEqual(self.medicao.fvs_aprovada_por, self.tecnico)

        self.client.force_login(self.auxiliar)
        pagina = self.client.get(reverse('abrir_rnc_pagina', args=[self.medicao.pk]))
        self.assertContains(pagina, 'revoga qualquer aprovação anterior')
        self.assertEqual(self.postar_rnc().status_code, 302)
        self.medicao.refresh_from_db()
        self.assertEqual(self.medicao.status_iso, 'NAO_CONFORME')
        self.assertEqual(self.medicao.percentual_concluido, 45)
        self.assertIsNone(self.medicao.fvs_aprovada_por)
        self.assertIsNone(self.medicao.fvs_aprovada_em)
        historico = list(HistoricoMedicao.objects.filter(medicao=self.medicao))
        self.assertEqual(len(historico), 2)
        self.assertEqual(historico[0].status_anterior, 'CONFORME')
        self.assertEqual(historico[0].status_novo, 'NAO_CONFORME')
        self.assertEqual(historico[0].autor, self.auxiliar)

    def test_usuario_comum_nao_pode_encerrar_rnc(self):
        self.client.force_login(self.auxiliar)
        self.postar_rnc()
        rnc = NaoConformidade.objects.get()
        response = self.client.post(reverse('tratar_rnc', args=[rnc.pk]), {
            'situacao': 'RESOLVIDA', 'acao_corretiva': 'Corrigida',
        })
        self.assertEqual(response.status_code, 403)
        rnc.refresh_from_db()
        self.assertEqual(rnc.situacao, 'ABERTA')
        self.assertEqual(EventoRNC.objects.count(), 1)

    def test_encerramento_exige_acao_e_nao_aprova_fvs(self):
        self.client.force_login(self.tecnico)
        self.postar_rnc()
        rnc = NaoConformidade.objects.get()
        url = reverse('tratar_rnc', args=[rnc.pk])
        invalid = self.client.post(url, {
            'situacao': 'RESOLVIDA', 'acao_corretiva': '', 'responsavel': '',
            'prazo': '', 'comentario': 'Fechar sem corrigir',
        })
        self.assertEqual(invalid.status_code, 200)
        rnc.refresh_from_db()
        self.assertEqual(rnc.situacao, 'ABERTA')
        valid = self.client.post(url, {
            'situacao': 'RESOLVIDA', 'acao_corretiva': 'Verga executada e inspecionada',
            'responsavel': str(self.tecnico.pk), 'prazo': '', 'comentario': 'Reparado',
        })
        self.assertEqual(valid.status_code, 302)
        rnc.refresh_from_db()
        self.medicao.refresh_from_db()
        self.assertEqual(rnc.situacao, 'RESOLVIDA')
        self.assertEqual(rnc.encerrada_por, self.tecnico)
        self.assertEqual(EventoRNC.objects.count(), 2)
        self.assertEqual(self.medicao.status_iso, 'NAO_CONFORME')

    def test_rnc_aberta_impede_aprovacao_fvs(self):
        self.client.force_login(self.tecnico)
        self.postar_rnc()
        response = self.client.post(reverse('avaliar_apartamento', args=[self.medicao.pk]), {
            'acao': 'manual', 'percentual': '100', 'status_iso': 'CONFORME',
            'etapa_atual': 'Acabamento',
        })
        self.assertEqual(response.status_code, 302)
        self.medicao.refresh_from_db()
        self.assertEqual(self.medicao.status_iso, 'NAO_CONFORME')
        self.assertEqual(self.medicao.percentual_concluido, 45)

    def test_auxiliar_pode_registrar_item_nao_conforme(self):
        self.client.force_login(self.auxiliar)
        resp = self.client.post(reverse('criar_item_fvs', args=[self.medicao.pk]), {
            'descricao': 'Conferir prumo', 'resultado': 'NAO_CONFORME',
            'observacao': 'Desvio observado',
        })
        self.assertEqual(resp.status_code, 302)
        item = ItemFVS.objects.get()
        self.assertEqual(item.verificado_por, self.auxiliar)
        self.assertEqual(EventoFVS.objects.count(), 1)

    def test_auxiliar_nao_pode_confirmar_item_conforme(self):
        self.client.force_login(self.auxiliar)
        response = self.client.post(reverse('criar_item_fvs', args=[self.medicao.pk]), {
            'descricao': 'Conferir prumo', 'resultado': 'CONFORME',
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ItemFVS.objects.count(), 0)

    def test_checklist_pendente_bloqueia_aprovacao_fvs(self):
        self.client.force_login(self.tecnico)
        self.client.post(reverse('criar_item_fvs', args=[self.medicao.pk]), {
            'descricao': 'Teste de estanqueidade', 'resultado': 'PENDENTE',
        })
        item = ItemFVS.objects.get()
        self.client.post(reverse('avaliar_apartamento', args=[self.medicao.pk]), {
            'acao': 'manual', 'percentual': '100', 'status_iso': 'CONFORME',
            'etapa_atual': 'Finalizado',
        })
        self.medicao.refresh_from_db()
        self.assertEqual(self.medicao.status_iso, 'PENDENTE')
        resp = self.client.post(reverse('editar_item_fvs', args=[self.medicao.pk, item.pk]), {
            'descricao': 'Teste de estanqueidade', 'resultado': 'CONFORME',
            'observacao': 'Inspecionado',
        })
        self.assertEqual(resp.status_code, 302)
        self.client.post(reverse('avaliar_apartamento', args=[self.medicao.pk]), {
            'acao': 'manual', 'percentual': '100', 'status_iso': 'CONFORME',
            'etapa_atual': 'Finalizado',
        })
        self.medicao.refresh_from_db()
        self.assertEqual(self.medicao.status_iso, 'CONFORME')
        self.assertEqual(self.medicao.fvs_aprovada_por, self.tecnico)
        self.assertEqual(self.medicao.percentual_concluido, 100)

    def test_modificar_checklist_reabre_fvs(self):
        self.client.force_login(self.tecnico)
        ItemFVS.objects.create(
            medicao=self.medicao, descricao='Inspeção inicial',
            resultado='CONFORME', verificado_por=self.tecnico,
        )
        self.client.post(reverse('avaliar_apartamento', args=[self.medicao.pk]), {
            'acao': 'manual', 'percentual': '100', 'status_iso': 'CONFORME',
            'etapa_atual': 'Finalizado',
        })
        self.client.post(reverse('criar_item_fvs', args=[self.medicao.pk]), {
            'descricao': 'Conferir vedação', 'resultado': 'CONFORME',
            'observacao': 'Necessita nova aprovação global',
        })
        self.medicao.refresh_from_db()
        self.assertEqual(self.medicao.percentual_concluido, 100)
        self.assertEqual(self.medicao.status_iso, 'PENDENTE')
        self.assertIsNone(self.medicao.fvs_aprovada_por)
        self.assertEqual(EventoFVS.objects.count(), 1)

    def test_planejamento_exige_staff_para_criar(self):
        self.client.force_login(self.auxiliar)
        response = self.client.post(reverse('planejamento'), {
            'torre': str(self.torre.pk),
            'mes_referencia': '2026-11', 'percentual_planejado': '70',
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(PlanejamentoMensal.objects.count(), 0)

    def test_planejamento_cadastra_e_atualiza_sem_duplicar(self):
        self.client.force_login(self.tecnico)
        url = reverse('planejamento')
        dados = {
            'torre': str(self.torre.pk),
            'mes_referencia': '2026-11', 'percentual_planejado': '70.50',
        }
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        self.assertEqual(PlanejamentoMensal.objects.count(), 1)
        painel = self.client.get(reverse('painel_principal'), {'mes': '2026-11'})
        self.assertEqual(painel.context['metas_grafico'], [70.5])
        dados['percentual_planejado'] = '75'
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        self.assertEqual(PlanejamentoMensal.objects.count(), 1)
        self.assertEqual(float(PlanejamentoMensal.objects.get().percentual_planejado), 75.0)

    def test_planejamento_rejeita_mes_invalido(self):
        self.client.force_login(self.tecnico)
        response = self.client.post(reverse('planejamento'), {
            'torre': str(self.torre.pk),
            'mes_referencia': '2026-13', 'percentual_planejado': '110',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PlanejamentoMensal.objects.count(), 0)

    def test_cadastro_restrito_e_cria_medicao_com_historico(self):
        self.client.force_login(self.auxiliar)
        self.assertEqual(self.client.get(reverse('cadastros')).status_code, 403)
        self.client.force_login(self.tecnico)
        response = self.client.post(reverse('cadastros'), {
            'acao': 'medicao', 'apartamento': str(self.apto.pk),
            'mes_referencia': '2026-12', 'etapa_atual': 'Revestimento',
            'percentual_concluido': '55',
        })
        self.assertEqual(response.status_code, 302)
        medicao = MedicaoMensal.objects.get(apartamento=self.apto, mes_referencia='2026-12')
        self.assertEqual(medicao.status_iso, 'PENDENTE')
        self.assertEqual(medicao.percentual_concluido, 55)
        self.assertEqual(medicao.historico.count(), 1)

    def test_cadastro_rejeita_medicao_duplicada(self):
        self.client.force_login(self.tecnico)
        response = self.client.post(reverse('cadastros'), {
            'acao': 'medicao', 'apartamento': str(self.apto.pk),
            'mes_referencia': '2026-11', 'etapa_atual': 'Alvenaria',
            'percentual_concluido': '30',
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(MedicaoMensal.objects.count(), 1)

    def test_cadastro_rejeita_andar_acima_do_total(self):
        self.client.force_login(self.tecnico)
        response = self.client.post(reverse('cadastros'), {
            'acao': 'apartamento', 'torre': str(self.torre.pk),
            'andar': '9', 'numero': '901',
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Apartamento.objects.count(), 1)

    def test_telas_operacionais_abrem_sem_erros(self):
        """Teste de navegação real: detecta templates ausentes e erros ao renderizar."""
        self.client.force_login(self.tecnico)
        urls = [
            reverse('painel_principal'),
            reverse('lista_rncs'),
            reverse('planejamento'),
            reverse('cadastros'),
            reverse('relatorios'),
            reverse('checklist_fvs', args=[self.medicao.pk]),
            reverse('abrir_rnc_pagina', args=[self.medicao.pk]),
            reverse('historico_medicao', args=[self.medicao.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_detalhe_rnc_carrega_com_eventos(self):
        self.client.force_login(self.tecnico)
        self.postar_rnc()
        rnc = NaoConformidade.objects.get()
        resp = self.client.get(reverse('detalhe_rnc', args=[rnc.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, rnc.titulo)
