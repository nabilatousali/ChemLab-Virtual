"""
Configuration d'administration de la plateforme.

Sécurité : les comptes utilisateurs étant créés via l'inscription publique,
l'administrateur ne peut PAS modifier les données sensibles d'un utilisateur
(adresse e-mail, mot de passe, identité, dates de connexion, rôles).
Il peut uniquement consulter ces informations et gérer l'état du compte
(activation / statut staff) pour la modération.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

# Désenregistrement de l'admin par défaut de Django.
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin utilisateur restreint : lecture seule sur les données sensibles."""

    # Champs sensibles protégés en lecture seule
    readonly_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "date_joined",
        "last_login",
        "groups",
        "user_permissions",
    )

    list_display = ("username", "email", "is_active", "is_staff", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)

    # Seule l'activation / le statut staff restent gérables.
    # En revanche, il n'est pas autorisé de :
    #   - changer le mot de passe (mot de passe en lecture seule),
    #   - importer / créer / supprimer des comptes utilisateurs,
    #   - modifier les informations personnelles et de connexion.
    fieldsets = (
        (None, {"fields": ("username", "first_name", "last_name", "email")}),
        (
            "État du compte",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Activité",
            {
                "fields": (
                    "date_joined",
                    "last_login",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        """Les comptes sont créés uniquement via l'inscription publique."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Interdiction de supprimer un compte utilisateur depuis l'admin."""
        return False

    # Le mot de passe ne doit jamais être modifiable ni affiché en clair.
    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                (None, {"fields": []}),
            )
        return super().get_fieldsets(request, obj)

    def get_urls(self):
        """Supprime la route « changer le mot de passe » de l'admin."""
        urls = super().get_urls()
        return [url for url in urls if "auth_user_password_change" not in str(url.name)]