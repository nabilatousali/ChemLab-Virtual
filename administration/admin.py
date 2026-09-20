"""Dashboard d'administration dédié (/administration/).

Utilise les informations gérées par Django admin (utilisateurs, expériences,
résultats, groupes, invitations, messages, paillasse) pour afficher un tableau
de bord complet : statistiques, activité récente et raccourcis de gestion.

Accès : staff uniquement (même règle que /admin/), sans aucun lien public.
"""

from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.utils import timezone

from experiments.models import Experiment
from groups.models import Group, GroupInvitation, GroupMessage
from laboratory.models import ExperimentResult, UserBenchReagent


def get_dashboard_stats():
    """Indicateurs plateforme de l'espace d'administration."""
    User = get_user_model()
    since_week = timezone.now() - timedelta(days=7)

    recent_users = list(
        User.objects.order_by("-date_joined").values("id", "username", "date_joined")[:5]
    )
    recent_results = list(
        ExperimentResult.objects.select_related("experiment", "user")
        .order_by("-completed_at")
        .values("experiment__title", "user__username", "is_successful", "completed_at")[:5]
    )

    return {
        "users_total": User.objects.count(),
        "users_active": User.objects.filter(is_active=True).count(),
        "users_week": User.objects.filter(date_joined__gte=since_week).count(),
        "experiments_total": Experiment.objects.count(),
        "experiments_published": Experiment.objects.filter(is_published=True).count(),
        "results_total": ExperimentResult.objects.count(),
        "results_success": ExperimentResult.objects.filter(is_successful=True).count(),
        "results_week": ExperimentResult.objects.filter(
            completed_at__gte=since_week
        ).count(),
        "groups_total": Group.objects.count(),
        "invitations_pending": GroupInvitation.objects.filter(
            status="pending"
        ).count(),
        "chat_messages": GroupMessage.objects.count(),
        "bench_reagents": UserBenchReagent.objects.count(),
        "recent_users": recent_users,
        "recent_results": recent_results,
    }


@staff_member_required
def dashboard(request):
    """Page d'administration : statistiques + activité + gestion."""
    return render(
        request,
        "administration/admin.html",
        {"admin_dashboard": get_dashboard_stats()},
    )
