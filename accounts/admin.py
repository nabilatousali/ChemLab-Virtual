"""
Configuration d'administration des comptes utilisateurs.

Politique : l'administrateur gère tout le cycle de vie SAUF la suppression
(dangereuse en cascade : résultats, groupes créés, messages...).
    - Création de comptes (avec mot de passe initial) ;
    - Droits : activation, statut staff / superuser, groupes, permissions ;
    - Modération : désactivation (is_active) pour bloquer une connexion ;
    - Identité (nom, e-mail...) modifiable uniquement à la création :
      ensuite, seul l'utilisateur concerné en est responsable.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

# Désenregistrement de l'admin par défaut de Django.
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin utilisateur complet : création, droits, modération."""

    list_display = ("username", "email", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)

    # Création : identité + mot de passe + droits initiaux.
    add_fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "email",
                    "password1",
                    "password2",
                )
            },
        ),
        (
            "Droits",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups")},
        ),
    )

    # Modification : identité protégée, état et droits gérables.
    fieldsets = (
        (None, {"fields": ("username", "first_name", "last_name", "email")}),
        (
            "État du compte et droits",
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
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        """Identité modifiable à la création seulement, jamais après."""
        if obj is None:
            return ("last_login", "date_joined")
        return (
            "username",
            "first_name",
            "last_name",
            "email",
            "last_login",
            "date_joined",
        )

    def has_delete_permission(self, request, obj=None):
        """Suppression interdite : cascade destructrice (résultats,
        groupes créés, messages, paillasse...). Modérer via is_active."""
        return False
