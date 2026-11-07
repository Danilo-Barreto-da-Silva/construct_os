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
