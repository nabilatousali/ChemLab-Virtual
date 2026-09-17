from django.contrib import admin
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from experiments.models import Experiment
from .admin import UserAdmin


class UserAdminSecurityTest(TestCase):
    """L'admin ne peut modifier aucune donnée sensible d'un utilisateur."""

    def setUp(self):
        self.admin_class = UserAdmin(User, admin.site)
        self.user = User.objects.create_user(
            username="victime",
            email="victime@example.com",
            password="MotDePasse123!",
        )

    def test_sensitive_fields_are_readonly(self):
        readonly = self.admin_class.get_readonly_fields(self.user)
        for field in ("username", "email", "first_name", "last_name", "date_joined", "last_login"):
            self.assertIn(field, readonly)

    def test_password_is_not_editable(self):
        fieldsets = self.admin_class.get_fieldsets(self.user)
        editable = [
            field
            for _, opts in fieldsets
            for field in opts["fields"]
        ]
        self.assertNotIn("password", editable)

    def test_no_add_permission(self):
        request = type("R", (), {})()
        self.assertFalse(self.admin_class.has_add_permission(request))

    def test_no_delete_permission(self):
        self.assertFalse(self.admin_class.has_delete_permission(None, obj=self.user))

    def test_password_change_url_removed(self):
        urls = self.admin_class.get_urls()
        names = {url.name for url in urls}
        self.assertNotIn("auth_user_password_change", names)


class VisitorAccessTest(TestCase):
    """Un visiteur n'accède qu'aux pages publiques (accueil, catalogue, détail)."""

    @classmethod
    def setUpTestData(cls):
        Experiment.objects.create(
            title="Dosage public",
            slug="dosage-public",
            short_description="Test",
            is_published=True,
        )

    def test_home_is_public(self):
        response = self.client.get(reverse("laboratory:home"))
        self.assertEqual(response.status_code, 200)

    def test_catalogue_is_public(self):
        response = self.client.get(reverse("experiments:catalogue"))
        self.assertEqual(response.status_code, 200)

    def test_detail_is_public(self):
        response = self.client.get(
            reverse("experiments:detail", args=["dosage-public"])
        )
        self.assertEqual(response.status_code, 200)

    def test_private_pages_redirect_to_login(self):
        private_urls = [
            reverse("laboratory:dashboard"),
            reverse("laboratory:history"),
            reverse("accounts:profile"),
            reverse("groups:list"),
        ]
        for url in private_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse('accounts:login')}?next={url}",
                )

    def test_private_pages_accessible_after_login(self):
        user = User.objects.create_user(username="user1", password="testpass123")
        self.client.force_login(user)
        response = self.client.get(reverse("laboratory:dashboard"))
        self.assertEqual(response.status_code, 200)


class RegisterViewTest(TestCase):

    def test_register_page_renders(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Créer un compte")

    def test_register_creates_user(self):
        self.client.post(reverse("accounts:register"), {
            "first_name": "Jean",
            "last_name": "Dupont",
            "username": "jeandupont",
            "email": "jean@example.com",
            "password": "TestPass123!",
            "password_confirmation": "TestPass123!",
        })
        self.assertTrue(User.objects.filter(username="jeandupont").exists())


class LoginViewTest(TestCase):

    def setUp(self):
        self.password = "TestPass123!"
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=self.password,
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Se connecter")

    def test_login_by_email_success_redirects(self):
        response = self.client.post(reverse("accounts:login"), {
            "email": "test@example.com",
            "password": self.password,
        })
        self.assertRedirects(response, reverse("laboratory:dashboard"))

    def test_login_wrong_password_shows_error(self):
        response = self.client.post(reverse("accounts:login"), {
            "email": "test@example.com",
            "password": "wrong",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], None, "Adresse e-mail ou mot de passe incorrect."
        )

    def test_login_unknown_email_shows_error(self):
        response = self.client.post(reverse("accounts:login"), {
            "email": "inconnu@example.com",
            "password": self.password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], None, "Adresse e-mail ou mot de passe incorrect."
        )
