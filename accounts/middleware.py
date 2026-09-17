"""Sécurité : exigence d'authentification par défaut.

Un visiteur (utilisateur non connecté) n'a accès qu'à :
    - la page d'accueil,
    - le catalogue des expériences,
    - la fiche détaillée d'une expérience,
    - les pages de connexion / inscription,
    - l'interface d'administration (accès staff),
    - les fichiers statiques et médias.

Toute autre ressource redirige vers la page de connexion (avec retour
sur la page souhaitée). Cette mesure applique le principe de moindre
privilège : même si une vue oubliait le décorateur ``login_required``,
elle reste protégée.
"""

from django.conf import settings
from django.shortcuts import redirect, resolve_url
from django.urls import Resolver404, resolve
from urllib.parse import quote


# Chemins toujours publics (administrés avant la résolution des vues).
PUBLIC_PATHS = (
    "/static/",
    "/media/",
    "/admin/",
    "/accounts/login/",
    "/accounts/register/",
)

# Noms de vues publiques (par résolution de l'URL).
PUBLIC_URL_NAMES = {
    "home",
    "catalogue",
    "detail",
    "login",
    "register",
}


class RequireLoginMiddleware:
    """Bloque l'accès aux pages privées pour les visiteurs anonymes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path_info

            is_public_path = any(path.startswith(p) for p in PUBLIC_PATHS)

            if not is_public_path:
                try:
                    match = resolve(path)
                except Resolver404:
                    # Ressource inexistante : on laisse Django renvoyer une 404.
                    return self.get_response(request)

                if match.url_name in PUBLIC_URL_NAMES:
                    return self.get_response(request)

                next_url = quote(request.get_full_path())
                login_url = resolve_url(settings.LOGIN_URL)
                return redirect(f"{login_url}?next={next_url}")

        return self.get_response(request)