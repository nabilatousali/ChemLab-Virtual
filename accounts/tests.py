from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

import re

from experiments.models import Experiment
from .admin import UserAdmin


class UserAdminSecurityTest(TestCase):
    """L'admin gère les comptes : création, droits, modération — sans suppression."""

    def setUp(self):
        self.admin_class = UserAdmin(User, admin.site)
        self.user = User.objects.create_user(
            username="victime",
            email="victime@example.com",
            password="MotDePasse123!",
        )

    def test_identity_readonly_on_change(self):
        readonly = self.admin_class.get_readonly_fields(None, self.user)
        for field in ("username", "email", "first_name", "last_name", "date_joined", "last_login"):
            self.assertIn(field, readonly)

    def test_rights_editable_on_change(self):
        readonly = self.admin_class.get_readonly_fields(None, self.user)
        for field in ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"):
            self.assertNotIn(field, readonly)

    def test_add_permission_granted(self):
        request = RequestFactory().get("/admin/")
        request.user = User.objects.create_superuser(
            username="root", email="root@example.com", password="TestPass123!"
        )
        self.assertTrue(self.admin_class.has_add_permission(request))

    def test_no_delete_permission(self):
        self.assertFalse(self.admin_class.has_delete_permission(None, obj=self.user))

    def test_password_change_url_available(self):
        urls = self.admin_class.get_urls()
        names = {url.name for url in urls}
        self.assertIn("auth_user_password_change", names)


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


class AdminDashboardTest(TestCase):
    """Le dashboard admin est privé : staff uniquement, invisible côté plateforme."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username="staff", password="TestPass123!", is_staff=True
        )
        cls.member = User.objects.create_user(
            username="member", password="TestPass123!"
        )

    def test_admin_index_redirects_anonymous_to_admin_login(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_admin_index_redirects_non_staff(self):
        self.client.force_login(self.member)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_staff_sees_dashboard_with_stats(self):
        Experiment.objects.create(
            title="Dosage",
            slug="dosage",
            short_description="Test",
            is_published=True,
        )
        self.client.force_login(self.staff)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tableau de bord")
        self.assertContains(response, "Utilisateurs inscrits")
        self.assertContains(response, "Nouveaux (7 jours)")
        self.assertContains(response, "Derniers comptes créés")
        self.assertContains(response, "Derniers résultats")

    def test_superuser_can_add_user_via_admin(self):
        admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="TestPass123!"
        )
        self.client.force_login(admin_user)
        response = self.client.post(reverse("admin:auth_user_add"), {
            "username": "nouveau",
            "email": "nouveau@example.com",
            "password1": "MotDePasse123!",
            "password2": "MotDePasse123!",
            "is_active": "on",
        })
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(username="nouveau")
        self.assertTrue(created.is_active)
        self.assertTrue(created.check_password("MotDePasse123!"))

    def test_superuser_can_deactivate_user_via_admin(self):
        admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="TestPass123!"
        )
        self.client.force_login(admin_user)
        response = self.client.post(
            reverse("admin:auth_user_change", args=[self.member.id]),
            {"username": "member", "email": "member@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)

    def test_no_admin_link_on_public_pages(self):
        for url in (
            reverse("laboratory:home"),
            reverse("experiments:catalogue"),
        ):
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), "/admin/")


class CustomAdminDashboardTest(TestCase):
    """L'espace /administration/ est réservé au staff, sans lien public."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(username="staff", password="TestPass123!", is_staff=True)
        cls.member = User.objects.create_user(username="member", password="TestPass123!")

    def test_anonymous_redirected_to_admin_login(self):
        response = self.client.get(reverse("administration_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_non_staff_redirected(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("administration_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_staff_sees_full_dashboard(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("administration_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tableau de bord")
        self.assertContains(response, "Gérer la plateforme")
        self.assertContains(response, "/admin/auth/user/")

    def test_no_public_link_to_custom_dashboard(self):
        for url in (
            reverse("laboratory:home"),
            reverse("experiments:catalogue"),
        ):
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), "/administration/")


class NavbarVariantsTest(TestCase):
    """La navbar visiteur et la navbar connectée sont différentes."""

    def navbar_section(self, response):
        content = response.content.decode()
        match = re.search(
            r'<nav class="navbar__nav".*?</nav>', content, re.DOTALL
        )
        self.assertIsNotNone(match)
        return match.group(0)

    def test_visitor_navbar_shows_only_public_links(self):
        response = self.client.get(reverse("laboratory:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "images/logo.png")
        navbar = self.navbar_section(response)
        for label in ("Accueil", "Catalogue", "S'inscrire"):
            with self.subTest(label=label):
                self.assertIn(label, navbar)
        for label in (
            "Expériences",
            "Laboratoire",
            "Paillasse",
            "Groupes",
            "Historique",
            "Profil",
            "Se connecter",
        ):
            with self.subTest(label=label):
                self.assertNotIn(label, navbar)

    def test_authenticated_navbar_shows_only_lab_links(self):
        user = User.objects.create_user(username="navuser", password="TestPass123!")
        self.client.force_login(user)
        response = self.client.get(reverse("laboratory:dashboard"))
        self.assertEqual(response.status_code, 200)
        navbar = self.navbar_section(response)
        for label in ("Expériences", "Laboratoire", "Paillasse", "Groupes", "Historique", "Profil"):
            with self.subTest(label=label):
                self.assertIn(label, navbar)
        for label in ("Accueil", "Catalogue", "S'inscrire", "Se connecter"):
            with self.subTest(label=label):
                self.assertNotIn(label, navbar)


class SecurityTrioTest(TestCase):
    """Redirect next validé, anti brute-force, activation e-mail."""

    def setUp(self):
        self.password = "TestPass123!"
        self.user = User.objects.create_user(
            username="secure", email="secure@example.com", password=self.password
        )

    def test_open_redirect_blocked(self):
        response = self.client.post(
            reverse("accounts:login") + "?next=http://evil.example/phish",
            {"email": "secure@example.com", "password": self.password},
        )
        self.assertRedirects(response, reverse("laboratory:dashboard"))

    def test_valid_next_preserved(self):
        bench_url = reverse("laboratory:bench")
        response = self.client.post(
            reverse("accounts:login") + f"?next={bench_url}",
            {"email": "secure@example.com", "password": self.password},
        )
        self.assertRedirects(response, bench_url)

    def test_bruteforce_locks_account(self):
        login_url = reverse("accounts:login")
        for _ in range(4):
            response = self.client.post(
                login_url,
                {"email": "secure@example.com", "password": "mauvais-mot-de-passe"},
            )
            self.assertEqual(response.status_code, 200)
        response = self.client.post(
            login_url,
            {"email": "secure@example.com", "password": "mauvais-mot-de-passe"},
        )
        self.assertEqual(response.status_code, 429)

    def register_new_user(self):
        self.client.post(reverse("accounts:register"), {
            "first_name": "Nadia",
            "last_name": "Test",
            "username": "nouveau",
            "email": "nouveau@example.com",
            "password": "TestPass123!",
            "password_confirmation": "TestPass123!",
        })
        return User.objects.get(username="nouveau")

    def test_register_creates_inactive_user(self):
        user = self.register_new_user()
        self.assertFalse(user.is_active)

    def test_login_refused_before_activation(self):
        self.register_new_user()
        response = self.client.post(reverse("accounts:login"), {
            "email": "nouveau@example.com",
            "password": "TestPass123!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pas encore activé")

    def test_activation_link_activates_and_logs_in(self):
        user = self.register_new_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        response = self.client.get(
            reverse("accounts:activate", kwargs={"uidb64": uid, "token": token})
        )
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertRedirects(response, reverse("laboratory:dashboard"))

    def test_invalid_activation_link_rejected(self):
        user = self.register_new_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        response = self.client.get(
            reverse("accounts:activate", kwargs={"uidb64": uid, "token": "invalide"})
        )
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertRedirects(response, reverse("accounts:login"))
