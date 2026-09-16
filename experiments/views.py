from django.shortcuts import get_object_or_404, render

from .models import Experiment


def catalogue(request):
    experiments = Experiment.objects.filter(
        is_published=True
    )

    return render(
        request,
        "experiments/catalogue.html",
        {
            "experiments": experiments,
        }
    )


def detail(request, slug):
    experiment = get_object_or_404(
        Experiment,
        slug=slug,
        is_published=True
    )

    return render(
        request,
        "experiments/detail.html",
        {
            "experiment": experiment,
        }
    )
