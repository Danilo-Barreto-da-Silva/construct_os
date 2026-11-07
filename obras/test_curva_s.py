"""Testes de regra de negócio e integração da Curva S física ponderada."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from .curva_s import cadastrar_servico, consolidar_curva, registrar_marco, atualizar_servico
from .models import (
    EventoMarcoServico, EventoServicoObra, MarcoServico, ServicoObra, Torre,
)


class CurvaSTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.gestor = User.objects.create_user(
            'gestor-curva', password='safe-password-test', is_staff=True,
        )
        cls.auxiliar = User.objects.create_user(
            'auxiliar-curva', password='safe-password-test',
        )
        cls.torre = Torre.objects.create(nome='Torre Curva S', total_andares=2)
        cls.outra = Torre.objects.create(nome='Outra Torre', total_andares=2)

    def servico(self, codigo='EST', peso='100', torre=None):
        return cadastrar_servico(
            autor=self.gestor, torre=torre or self.torre,
            codigo=codigo, descricao=f'Atividade {codigo}',
            peso_percentual=Decimal(peso),
        )

    def marco(self, servico, mes, previsto=None, realizado=None):
        return registrar_marco(
            autor=self.gestor, servico=servico, mes_referencia=mes,
            previsto_acumulado=Decimal(str(previsto)) if previsto is not None else None,
            realizado_acumulado=Decimal(str(realizado)) if realizado is not None else None,
            observacao='Simulação de engenharia / teste',
        )

    def test_pesos_ponderados_nao_sao_media_simples(self):
        estrutura = self.servico('EST', '30')
        alvenaria = self.servico('ALV', '20')
        acabamento = self.servico('ACB', '50')
        self.marco(estrutura, '2026-10', previsto=50, realizado=20)
        self.marco(alvenaria, '2026-10', previsto=100, realizado=100)
        self.marco(acabamento, '2026-10', previsto=0, realizado=0)
        self.marco(estrutura, '2026-11', previsto=100, realizado=80)
        self.marco(alvenaria, '2026-11', previsto=100, realizado=100)
        self.marco(acabamento, '2026-11', previsto=40, realizado=20)
        curva = consolidar_curva(self.torre)
        self.assertEqual(curva['peso_total'], Decimal('100.00'))
        self.assertTrue(curva['pesos_ok'])
        self.assertEqual(curva['previstos'], [35.0, 70.0])
        self.assertEqual(curva['realizados'], [26.0, 54.0])
        self.assertEqual(curva['linhas'][1]['desvio'], Decimal('-16.00'))

    def test_peso_incompleto_oculta_indicador(self):
        servico = self.servico('EST', '30')
        self.marco(servico, '2026-11', previsto=100, realizado=100)
        curva = consolidar_curva(self.torre)
        self.assertFalse(curva['pesos_ok'])
        self.assertIsNone(curva['linhas'][0]['previsto'])
        self.assertIsNone(curva['linhas'][0]['realizado'])
        self.assertIsNone(curva['ultima_linha_completa'])

    def test_lancamento_faltante_nao_vira_zero(self):
        est = self.servico('EST', '60')
        alv = self.servico('ALV', '40')
        self.marco(est, '2026-11', previsto=50, realizado=25)
        self.marco(alv, '2026-11', previsto=50)
        curva = consolidar_curva(self.torre)
        linha = curva['linhas'][0]
        self.assertEqual(linha['previsto'], Decimal('50.00'))
        self.assertIsNone(linha['realizado'])
        self.assertEqual(linha['n_previsto'], 2)
        self.assertEqual(linha['n_realizado'], 1)
        self.assertEqual(curva['realizados'], [None])

    def test_peso_que_ultrapassa_100_e_rejeitado(self):
        self.servico('EST', '60')
        with self.assertRaises(ValidationError):
            self.servico('ALV', '41')
        self.assertEqual(ServicoObra.objects.count(), 1)

    def test_codigo_duplicado_apenas_na_mesma_torre(self):
        self.servico('EST', '50')
        with self.assertRaises(ValidationError):
            self.servico('EST', '25')
        self.servico('EST', '100', torre=self.outra)
        self.assertEqual(ServicoObra.objects.count(), 2)

    def test_usuarios_comuns_nao_editam_servicos_ou_marcos(self):
        with self.assertRaises(PermissionDenied):
            cadastrar_servico(
                autor=self.auxiliar, torre=self.torre, codigo='ALV',
                descricao='Alvenaria', peso_percentual=Decimal('10')
            )
        servico = self.servico()
        with self.assertRaises(PermissionDenied):
            registrar_marco(
                autor=self.auxiliar, servico=servico, mes_referencia='2026-11',
                previsto_acumulado=Decimal('20'),
            )

    def test_acumulado_nao_pode_retroceder(self):
        servico = self.servico()
        self.marco(servico, '2026-10', previsto=30, realizado=20)
        self.marco(servico, '2026-11', previsto=60, realizado=40)
        eventos = EventoMarcoServico.objects.count()
        with self.assertRaises(ValidationError):
            self.marco(servico, '2026-11', previsto=25)
        with self.assertRaises(ValidationError):
            self.marco(servico, '2026-11', realizado=10)
        atual = MarcoServico.objects.get(servico=servico, mes_referencia='2026-11')
        self.assertEqual(atual.previsto_acumulado, Decimal('60'))
        self.assertEqual(atual.realizado_acumulado, Decimal('40'))
        self.assertEqual(EventoMarcoServico.objects.count(), eventos)

    def test_entrada_antiga_nao_pode_ultrapassar_mes_seguinte(self):
        servico = self.servico()
        self.marco(servico, '2026-10', previsto=30, realizado=20)
        self.marco(servico, '2026-11', previsto=60, realizado=40)
        with self.assertRaises(ValidationError):
            self.marco(servico, '2026-10', previsto=65)

    def test_uma_atualizacao_preserva_o_outro_campo(self):
        servico = self.servico()
        self.marco(servico, '2026-11', previsto=30, realizado=10)
        marco, alterou = self.marco(servico, '2026-11', previsto=40)
        self.assertTrue(alterou)
        self.assertEqual(marco.previsto_acumulado, Decimal('40'))
        self.assertEqual(marco.realizado_acumulado, Decimal('10'))
        self.assertEqual(EventoMarcoServico.objects.count(), 2)
        evento = EventoMarcoServico.objects.order_by('-pk').first()
        self.assertEqual(evento.previsto_anterior, Decimal('30'))
        self.assertEqual(evento.previsto_novo, Decimal('40'))
        self.assertEqual(evento.realizado_anterior, Decimal('10'))
        self.assertEqual(evento.realizado_novo, Decimal('10'))
        self.assertEqual(evento.autor, self.gestor)

    def test_repetir_valores_nao_gera_evento_duplicado(self):
        servico = self.servico()
        self.marco(servico, '2026-11', previsto=30, realizado=10)
        _, alterou = self.marco(servico, '2026-11', previsto=30, realizado=10)
        self.assertFalse(alterou)
        self.assertEqual(EventoMarcoServico.objects.count(), 1)

    def test_valores_fora_de_zero_a_cem_e_rejeitados(self):
        servico = self.servico()
        with self.assertRaises(ValidationError):
            self.marco(servico, '2026-11', previsto=110)
        with self.assertRaises(ValidationError):
            self.marco(servico, '2026-11', realizado=-1)
        self.assertEqual(MarcoServico.objects.count(), 0)

    def test_mes_invalido_rejeitado(self):
        servico = self.servico()
        with self.assertRaises(ValidationError):
            self.marco(servico, '2026-13', previsto=10)
        self.assertFalse(MarcoServico.objects.exists())

    def test_protecao_contra_apagar_servico_com_lancamentos(self):
        servico = self.servico()
        self.marco(servico, '2026-11', previsto=10)
        with self.assertRaises(ProtectedError):
            servico.delete()

    def test_pagina_nova_abre_para_usuario_comum_em_somente_leitura(self):
        self.servico()
        self.client.force_login(self.auxiliar)
        resp = self.client.get(reverse('planejamento_fisico'), {'torre': self.torre.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Curva S física ponderada')
        self.assertContains(resp, 'Apenas equipe autorizada')
        self.assertEqual(self.client.post(
            reverse('planejamento_fisico'), {
                'acao': 'servico', 'torre': self.torre.pk,
                'codigo': 'ALV', 'descricao': 'Alvenaria',
                'peso_percentual': '30',
            }
        ).status_code, 403)

    def test_formulario_cadastra_servico_e_impede_excesso(self):
        self.client.force_login(self.gestor)
        url = reverse('planejamento_fisico') + f'?torre={self.torre.pk}'
        dados = {'acao': 'servico', 'torre': self.torre.pk, 'codigo': 'EST',
                 'descricao': 'Estrutura', 'peso_percentual': '75'}
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        self.assertEqual(ServicoObra.objects.get().peso_percentual, Decimal('75'))
        dados.update(codigo='ALV', descricao='Alvenaria', peso_percentual='40')
        invalido = self.client.post(url, dados)
        self.assertEqual(invalido.status_code, 200)
        self.assertContains(invalido, 'não podem ultrapassar 100%')
        self.assertEqual(ServicoObra.objects.count(), 1)

    def test_formulario_registra_e_atualiza_marco_sem_duplicar(self):
        servico = self.servico()
        self.client.force_login(self.gestor)
        url = reverse('planejamento_fisico') + f'?torre={self.torre.pk}'
        dados = {
            'acao': 'marco', 'servico': servico.pk, 'mes_referencia': '2026-10',
            'previsto_acumulado': '50', 'realizado_acumulado': '25',
            'observacao': 'Planejamento inicial',
        }
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        self.assertEqual(MarcoServico.objects.count(), 1)
        dados['previsto_acumulado'] = '60'
        dados['realizado_acumulado'] = ''
        dados['observacao'] = 'Revisão do planejado'
        resposta = self.client.post(url, dados)
        self.assertEqual(resposta.status_code, 302)
        marco = MarcoServico.objects.get()
        self.assertEqual(marco.previsto_acumulado, Decimal('60'))
        self.assertEqual(marco.realizado_acumulado, Decimal('25'))
        self.assertEqual(EventoMarcoServico.objects.count(), 2)

    def test_formulario_nao_aceita_servico_de_torre_diferente(self):
        servico = self.servico(torre=self.outra)
        self.client.force_login(self.gestor)
        url = reverse('planejamento_fisico') + f'?torre={self.torre.pk}'
        resposta = self.client.post(url, {
            'acao': 'marco', 'servico': servico.pk,
            'mes_referencia': '2026-11',
            'previsto_acumulado': '20', 'realizado_acumulado': '',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(MarcoServico.objects.exists())

    def test_relatorio_mostra_serie_ponderada_quando_completa(self):
        servico = self.servico()
        self.marco(servico, '2026-11', previsto=75, realizado=60)
        self.client.force_login(self.gestor)
        resp = self.client.get(reverse('relatorios'), {'mes': '2026-11', 'torre': self.torre.pk})
        self.assertEqual(resp.status_code, 200)
        resumo = resp.context['resumo_curvas'][0]
        self.assertEqual(resumo['linha']['previsto'], Decimal('75.00'))
        self.assertEqual(resumo['linha']['realizado'], Decimal('60.00'))
        self.assertContains(resp, 'Curva S física por atividades')

    def test_csv_de_servicos_exige_staff_e_e_neutralizado(self):
        servico = self.servico(codigo='=SOMAR(1;1)')
        self.marco(servico, '2026-11', previsto=10)
        url = reverse('exportar_servicos_csv') + '?mes=2026-11'
        self.client.force_login(self.auxiliar)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.gestor)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/csv', resp['Content-Type'])
        self.assertIn("'=SOMAR(1;1)", resp.content.decode('utf-8-sig'))
        self.assertIn('Planejado acumulado', resp.content.decode('utf-8-sig'))

    def test_edicao_de_servico_antes_de_medir_gera_auditoria(self):
        servico = self.servico('EST', '40')
        servico, alterou = atualizar_servico(
            autor=self.gestor, servico_id=servico.pk,
            descricao='Estrutura revisada', peso_percentual=Decimal('50'),
        )
        self.assertTrue(alterou)
        self.assertEqual(servico.peso_percentual, Decimal('50'))
        self.assertEqual(servico.descricao, 'Estrutura revisada')
        evento = EventoServicoObra.objects.get(servico=servico)
        self.assertEqual(evento.autor, self.gestor)
        self.assertEqual(evento.peso_anterior, Decimal('40'))
        self.assertEqual(evento.peso_novo, Decimal('50'))

    def test_peso_congelado_apos_lancamento_mas_descricao_pode_ser_corrigida(self):
        servico = self.servico('EST', '100')
        self.marco(servico, '2026-11', previsto=20)
        with self.assertRaises(ValidationError):
            atualizar_servico(
                autor=self.gestor, servico_id=servico.pk,
                descricao='Estrutura', peso_percentual=Decimal('90'),
            )
        servico.refresh_from_db()
        self.assertEqual(servico.peso_percentual, Decimal('100'))
        self.assertEqual(EventoServicoObra.objects.count(), 0)
        _, alterou = atualizar_servico(
            autor=self.gestor, servico_id=servico.pk,
            descricao='Estrutura revisada', peso_percentual=Decimal('100'),
        )
        self.assertTrue(alterou)
        self.assertEqual(EventoServicoObra.objects.count(), 1)

    def test_formulario_de_edicao_tem_permissao_e_evita_trocar_peso_congelado(self):
        servico = self.servico('EST', '100')
        url = reverse('planejamento_fisico') + f'?torre={self.torre.pk}'
        dados = {'acao': 'editar_servico', 'servico_id': servico.pk,
                 'descricao': 'Estrutura final', 'peso_percentual': '100'}
        self.client.force_login(self.auxiliar)
        self.assertEqual(self.client.post(url, dados).status_code, 403)
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        servico.refresh_from_db()
        self.assertEqual(servico.descricao, 'Estrutura final')
        self.assertEqual(EventoServicoObra.objects.count(), 1)
        self.marco(servico, '2026-11', realizado=20)
        dados['peso_percentual'] = '90'
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        servico.refresh_from_db()
        self.assertEqual(servico.peso_percentual, Decimal('100'))
        self.assertEqual(EventoServicoObra.objects.count(), 1)

    def test_painel_filtrado_exibe_curva_ponderada_independente(self):
        servico = self.servico()
        self.marco(servico, '2026-11', previsto=60, realizado=40)
        self.client.force_login(self.gestor)
        resp = self.client.get(reverse('painel_principal'), {
            'torre': self.torre.pk, 'mes': '2026-11',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['curva_servicos']['previstos'], [60.0])
        self.assertEqual(resp.context['curva_servicos']['realizados'], [40.0])
        self.assertContains(resp, 'Curva S física da torre selecionada')
        self.assertContains(resp, 'Planejado por serviços')

    def test_painel_geral_nao_mistura_curvas_entre_torres(self):
        servico = self.servico()
        self.marco(servico, '2026-11', previsto=60, realizado=40)
        self.client.force_login(self.gestor)
        geral = self.client.get(reverse('painel_principal'), {'mes': '2026-11'})
        self.assertEqual(geral.status_code, 200)
        self.assertIsNone(geral.context['curva_servicos'])
        self.assertNotContains(geral, 'Curva S física da torre selecionada')
        andar = self.client.get(reverse('painel_principal'), {
            'torre': self.torre.pk, 'andar': '1', 'mes': '2026-11',
        })
        self.assertIsNone(andar.context['curva_servicos'])
