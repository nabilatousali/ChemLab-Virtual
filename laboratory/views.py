from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from experiments.models import Experiment


def home(request):
    return render(request, "laboratory/home.html")


@login_required
def dashboard(request):
    experiments = Experiment.objects.filter(is_published=True)
    return render(request, "laboratory/dashboard.html", {"experiments": experiments})


@login_required
def laboratory_workspace(request, slug):
    experiment = get_object_or_404(Experiment, slug=slug, is_published=True)

    context = {
        "experiment": experiment,
        "materials": experiment.materials.select_related("material").order_by("order"),
        "reagents": experiment.reagents.select_related("reagent").order_by("order"),
        "steps": experiment.steps.order_by("number"),
        "indicators": experiment.indicators.select_related("indicator").order_by("order"),
    }
    return render(request, "laboratory/workspace.html", context)