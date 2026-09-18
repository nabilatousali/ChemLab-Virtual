"""Tableau de bord privé de l'administration ChemLab (/admin/).

Espace réservé au staff via l'admin Django : aucune entrée vers /admin/
n'est exposée sur la plateforme publique (ni navbar, ni pages).
"""

from django.contrib.auth import get_user_model

from experiments.models import Experiment
from groups.models import Group, GroupInvitation
from laboratory.models import ExperimentResult, UserBenchReagent


def dashboard_stats(request):
    """Injecte les indicateurs du dashboard sur l'accueil de l'admin."""
    if request.path != "/admin/" or not request.user.is_staff:
        return {}

    User = get_user_model()
    return {
        "admin_dashboard": {
            "users_total": User.objects.count(),
            "users_active": User.objects.filter(is_active=True).count(),
            "experiments_total": Experiment.objects.count(),
            "experiments_published": Experiment.objects.filter(
                is_published=True
            ).count(),
            "results_total": ExperimentResult.objects.count(),
            "results_success": ExperimentResult.objects.filter(
                is_successful=True
            ).count(),
            "groups_total": Group.objects.count(),
            "invitations_pending": GroupInvitation.objects.filter(
                status="pending"
            ).count(),
            "bench_reagents": UserBenchReagent.objects.count(),
        }
    }
