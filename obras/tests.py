from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


class SecurityTests(TestCase):
    def test_login_does_not_create_default_admin(self):
        self.client.get(reverse("login_sistema"))
        self.assertFalse(get_user_model().objects.filter(username="adm").exists())

    def test_demo_requires_authentication(self):
        response = self.client.post(reverse("popular_dados_demo"), {"confirmar_substituicao": "SIM"})
        self.assertEqual(response.status_code, 302)

    @override_settings(DEBUG=False)
    def test_demo_forbidden_outside_debug(self):
        user = get_user_model().objects.create_superuser("owner", "owner@example.com", "safe-password-for-test")
        self.client.force_login(user)
        response = self.client.post(reverse("popular_dados_demo"), {"confirmar_substituicao": "SIM"})
        self.assertEqual(response.status_code, 403)

    @override_settings(DEBUG=True)
    def test_demo_requires_explicit_confirmation(self):
        user = get_user_model().objects.create_superuser("owner", "owner@example.com", "safe-password-for-test")
        self.client.force_login(user)
        response = self.client.post(reverse("popular_dados_demo"))
        self.assertEqual(response.status_code, 302)

    def test_logout_rejects_get(self):
        response = self.client.get(reverse("logout_sistema"))
        self.assertEqual(response.status_code, 405)

    def test_login_rejects_external_redirect(self):
        user = get_user_model().objects.create_user("tester", password="safe-password-for-test")
        response = self.client.post(reverse("login_sistema"), {
            "username": "tester", "password": "safe-password-for-test",
            "next": "https://attacker.example/"
        })
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    @override_settings(DEBUG=True)
    def test_demo_never_deletes_existing_towers(self):
        from .models import Torre
        user = get_user_model().objects.create_superuser("owner2", "owner2@example.com", "safe-password-for-test")
        self.client.force_login(user)
        tower = Torre.objects.create(nome="Obra real")
        self.client.post(reverse("popular_dados_demo"), {"confirmar_substituicao": "SIM"})
        self.assertTrue(Torre.objects.filter(pk=tower.pk).exists())
        self.assertEqual(Torre.objects.count(), 1)

    def test_manual_measurement_keeps_100_percent_with_pending_fvs(self):
        from .models import Torre, Apartamento, MedicaoMensal
        user = get_user_model().objects.create_user("engineer", password="safe-password-for-test")
        self.client.force_login(user)
        torre = Torre.objects.create(nome="Torre teste")
        apartamento = Apartamento.objects.create(torre=torre, andar=1, numero="101")
        medicao = MedicaoMensal.objects.create(apartamento=apartamento, mes_referencia="2026-11")
        response = self.client.post(reverse("avaliar_apartamento", args=[medicao.pk]), {
            "acao": "manual", "percentual": "100", "status_iso": "PENDENTE",
            "etapa_atual": "Acabamento", "laudo_ia": "FVS aguardando inspeção",
        })
        self.assertEqual(response.status_code, 302)
        medicao.refresh_from_db()
        self.assertEqual(medicao.percentual_concluido, 100)
        self.assertEqual(medicao.status_iso, "PENDENTE")

    def test_manual_measurement_rejects_invalid_percent(self):
        from .models import Torre, Apartamento, MedicaoMensal
        user = get_user_model().objects.create_user("tester2", password="safe-password-for-test")
        self.client.force_login(user)
        torre = Torre.objects.create(nome="Torre teste")
        apartamento = Apartamento.objects.create(torre=torre, andar=1, numero="101")
        medicao = MedicaoMensal.objects.create(apartamento=apartamento, mes_referencia="2026-11", percentual_concluido=25)
        self.client.post(reverse("avaliar_apartamento", args=[medicao.pk]), {
            "acao": "manual", "percentual": "150", "status_iso": "CONFORME",
            "etapa_atual": "Alvenaria",
        })
        medicao.refresh_from_db()
        self.assertEqual(medicao.percentual_concluido, 25)

    def test_invalid_floor_filter_does_not_crash(self):
        user = get_user_model().objects.create_user("tester3", password="safe-password-for-test")
        self.client.force_login(user)
        response = self.client.get(reverse("painel_principal"), {"andar": "nao-numerico"})
        self.assertEqual(response.status_code, 200)

    def test_historical_chart_uses_only_registered_months(self):
        from .models import Torre, Apartamento, MedicaoMensal
        user = get_user_model().objects.create_user("historico", password="safe-password-for-test")
        self.client.force_login(user)
        torre = Torre.objects.create(nome="Torre histórico")
        apto = Apartamento.objects.create(torre=torre, andar=1, numero="101")
        MedicaoMensal.objects.create(apartamento=apto, mes_referencia="2026-10", percentual_concluido=20)
        MedicaoMensal.objects.create(apartamento=apto, mes_referencia="2026-11", percentual_concluido=60)
        response = self.client.get(reverse("painel_principal"), {"mes": "2026-11"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["meses_grafico"], ["2026-10", "2026-11"])
        self.assertEqual(response.context["valores_grafico"], [20.0, 60.0])

    def test_invalid_tower_filter_does_not_crash(self):
        user = get_user_model().objects.create_user("invalidtower", password="safe-password-for-test")
        self.client.force_login(user)
        response = self.client.get(reverse("painel_principal"), {"torre": "invalido"})
        self.assertEqual(response.status_code, 200)

    def test_regular_user_cannot_approve_fvs(self):
        from .models import Torre, Apartamento, MedicaoMensal, HistoricoMedicao
        user = get_user_model().objects.create_user("auxiliar", password="safe-password-for-test")
        self.client.force_login(user)
        torre = Torre.objects.create(nome="Torre restrita")
        apto = Apartamento.objects.create(torre=torre, andar=1, numero="101")
        medicao = MedicaoMensal.objects.create(apartamento=apto, percentual_concluido=80)
        response = self.client.post(reverse("avaliar_apartamento", args=[medicao.pk]), {
            "acao": "manual", "percentual": "100", "status_iso": "CONFORME",
            "etapa_atual": "Concluído", "laudo_ia": "Inspeção aprovada",
        })
        self.assertEqual(response.status_code, 403)
        medicao.refresh_from_db()
        self.assertEqual(medicao.percentual_concluido, 80)
        self.assertEqual(medicao.status_iso, "PENDENTE")
        self.assertEqual(HistoricoMedicao.objects.count(), 0)

    def test_fvs_sem_checklist_nao_pode_ser_aprovada(self):
        from .models import Torre, Apartamento, MedicaoMensal, HistoricoMedicao
        tecnico = get_user_model().objects.create_user(
            "tecnico_fvs_vazia", password="safe-password-for-test", is_staff=True
        )
        torre = Torre.objects.create(nome="Obra checklist vazio")
        apto = Apartamento.objects.create(torre=torre, andar=1, numero="001")
        medicao = MedicaoMensal.objects.create(
            apartamento=apto, percentual_concluido=35, status_iso="PENDENTE"
        )
        self.client.force_login(tecnico)
        response = self.client.post(reverse("avaliar_apartamento", args=[medicao.pk]), {
            "acao": "manual", "percentual": "100", "status_iso": "CONFORME",
            "etapa_atual": "Finalizado",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastre e verifique pelo menos um item")
        medicao.refresh_from_db()
        self.assertEqual(medicao.percentual_concluido, 35)
        self.assertEqual(medicao.status_iso, "PENDENTE")
        self.assertIsNone(medicao.fvs_aprovada_por)
        self.assertFalse(HistoricoMedicao.objects.filter(medicao=medicao).exists())

    def test_usuario_comum_nao_pode_rebaixar_ou_editar_fvs_aprovada(self):
        from .models import Torre, Apartamento, MedicaoMensal, HistoricoMedicao, ItemFVS
        gestor = get_user_model().objects.create_user(
            "gestor_fvs_trava", password="safe-password-for-test", is_staff=True
        )
        auxiliar = get_user_model().objects.create_user(
            "auxiliar_fvs_trava", password="safe-password-for-test"
        )
        torre = Torre.objects.create(nome="Obra FVS bloqueada")
        apto = Apartamento.objects.create(torre=torre, andar=1, numero="002")
        medicao = MedicaoMensal.objects.create(
            apartamento=apto, percentual_concluido=100, status_iso="PENDENTE"
        )
        ItemFVS.objects.create(
            medicao=medicao, descricao="Inspeção final", resultado="CONFORME",
            verificado_por=gestor,
        )
        url = reverse("avaliar_apartamento", args=[medicao.pk])
        self.client.force_login(gestor)
        self.assertEqual(self.client.post(url, {
            "acao": "manual", "percentual": "100", "status_iso": "CONFORME",
            "etapa_atual": "Finalizado", "laudo_ia": "Conferido pela engenharia",
        }).status_code, 302)
        medicao.refresh_from_db()
        self.assertEqual(medicao.status_iso, "CONFORME")
        autor_aprovacao = medicao.fvs_aprovada_por
        horario_aprovacao = medicao.fvs_aprovada_em
        historico_inicial = HistoricoMedicao.objects.filter(medicao=medicao).count()
        self.client.force_login(auxiliar)
        for status in ("PENDENTE", "NAO_CONFORME", "CONFORME"):
            response = self.client.post(url, {
                "acao": "manual", "percentual": "25", "status_iso": status,
                "etapa_atual": "Alteração não autorizada",
                "laudo_ia": "Texto modificado",
            })
            self.assertEqual(response.status_code, 403)
            medicao.refresh_from_db()
            self.assertEqual(medicao.status_iso, "CONFORME")
            self.assertEqual(medicao.percentual_concluido, 100)
            self.assertEqual(medicao.fvs_aprovada_por, autor_aprovacao)
            self.assertEqual(medicao.fvs_aprovada_em, horario_aprovacao)
            self.assertEqual(
                HistoricoMedicao.objects.filter(medicao=medicao).count(), historico_inicial
            )

    def test_staff_approval_records_author_and_previous_values(self):
        from .models import Torre, Apartamento, MedicaoMensal, HistoricoMedicao
        user = get_user_model().objects.create_user("engenheira", password="safe-password-for-test", is_staff=True)
        self.client.force_login(user)
        torre = Torre.objects.create(nome="Torre de auditoria")
        apto = Apartamento.objects.create(torre=torre, andar=2, numero="201")
        medicao = MedicaoMensal.objects.create(apartamento=apto, percentual_concluido=60, status_iso="PENDENTE")
        from .models import ItemFVS
        ItemFVS.objects.create(
            medicao=medicao, descricao="Revisão do acabamento", resultado="CONFORME",
            verificado_por=user,
        )
        response = self.client.post(reverse("avaliar_apartamento", args=[medicao.pk]), {
            "acao": "manual", "percentual": "100", "status_iso": "CONFORME",
            "etapa_atual": "Pintura concluída", "laudo_ia": "FVS inspecionada",
        })
        self.assertEqual(response.status_code, 302)
        medicao.refresh_from_db()
        self.assertEqual(medicao.percentual_concluido, 100)
        self.assertEqual(medicao.fvs_aprovada_por, user)
        self.assertIsNotNone(medicao.fvs_aprovada_em)
        evento = HistoricoMedicao.objects.get(medicao=medicao)
        self.assertEqual(evento.autor, user)
        self.assertEqual(evento.percentual_anterior, 60)
        self.assertEqual(evento.percentual_novo, 100)
        self.assertEqual(evento.status_anterior, "PENDENTE")
        self.assertEqual(evento.status_novo, "CONFORME")

        pagina = self.client.get(reverse("historico_medicao", args=[medicao.pk]))
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, "engenheira")
        self.assertContains(pagina, "FVS inspecionada")

    def test_fvs_approval_cleared_when_reopened(self):
        from .models import Torre, Apartamento, MedicaoMensal
        user = get_user_model().objects.create_user("responsavel", password="safe-password-for-test", is_staff=True)
        self.client.force_login(user)
        torre = Torre.objects.create(nome="Torre")
        apto = Apartamento.objects.create(torre=torre, andar=1, numero="102")
        medicao = MedicaoMensal.objects.create(apartamento=apto)
        from .models import ItemFVS
        ItemFVS.objects.create(
            medicao=medicao, descricao="Inspeção concluída", resultado="CONFORME",
            verificado_por=user,
        )
        url = reverse("avaliar_apartamento", args=[medicao.pk])
        self.client.post(url, {"acao": "manual", "percentual": "100", "status_iso": "CONFORME", "etapa_atual": "Fim"})
        medicao.refresh_from_db()
        self.assertEqual(medicao.fvs_aprovada_por, user)
        self.client.post(url, {"acao": "manual", "percentual": "100", "status_iso": "NAO_CONFORME", "etapa_atual": "Fim"})
        medicao.refresh_from_db()
        self.assertIsNone(medicao.fvs_aprovada_por)
        self.assertIsNone(medicao.fvs_aprovada_em)
        self.assertEqual(medicao.historico.count(), 2)

    @override_settings(GEMINI_API_KEY="chave-ficticia-teste")
    def test_ai_suggestion_does_not_approve_or_change_progress(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import Torre, Apartamento, MedicaoMensal, HistoricoMedicao
        user = get_user_model().objects.create_user("vistoriador", password="safe-password-for-test")
        self.client.force_login(user)
        torre = Torre.objects.create(nome="Torre IA")
        apto = Apartamento.objects.create(torre=torre, andar=1, numero="103")
        medicao = MedicaoMensal.objects.create(apartamento=apto, percentual_concluido=40, status_iso="PENDENTE")
        with patch("obras.views.analisar_video_obra") as mock_analise:
            mock_analise.return_value = SimpleNamespace(
                etapa_identificada="Revestimento",
                percentual_sugerido=100,
                status_iso_sugerido="CONFORME",
                resumo_tecnico="Resultado simulado no teste",
            )
            video = SimpleUploadedFile("ensaio.mp4", b"arquivo-ficticio", content_type="video/mp4")
            response = self.client.post(
                reverse("avaliar_apartamento", args=[medicao.pk]),
                {"acao": "ia_video", "video_vistoria": video},
            )
        self.assertEqual(response.status_code, 302)
        medicao.refresh_from_db()
        self.assertEqual(medicao.percentual_concluido, 40)
        self.assertEqual(medicao.status_iso, "PENDENTE")
        self.assertIn("Resultado simulado", medicao.sugestao_ia)
        self.assertEqual(HistoricoMedicao.objects.get(medicao=medicao).origem, "SUGESTAO_IA")
