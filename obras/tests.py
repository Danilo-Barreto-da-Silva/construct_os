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
