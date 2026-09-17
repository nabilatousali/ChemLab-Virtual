import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from experiments.models import Experiment
from .models import Reagent, ExperimentResult, ResultValue


def home(request):
    return render(request, "laboratory/home.html")


@login_required
def dashboard(request):
    experiments = Experiment.objects.filter(is_published=True)
    return render(request, "laboratory/dashboard.html", {"experiments": experiments})


@login_required
def laboratory_workspace(request, slug):
    experiment = get_object_or_404(Experiment, slug=slug, is_published=True)
    request.session["last_experiment_slug"] = slug

    context = {
        "experiment": experiment,
        "materials": experiment.materials.select_related("material").order_by("order"),
        "reagents": experiment.reagents.select_related("reagent").order_by("order"),
        "steps": experiment.steps.order_by("number"),
        "indicators": experiment.indicators.select_related("indicator").order_by("order"),
    }
    return render(request, "laboratory/workspace.html", context)


@login_required
def laboratory_redirect(request):
    """Ouvre la dernière expérience ouverte, sinon le tableau de bord."""
    slug = request.session.get("last_experiment_slug")
    if slug and Experiment.objects.filter(slug=slug, is_published=True).exists():
        return redirect("laboratory:workspace", slug=slug)
    return redirect("laboratory:dashboard")


@login_required
def history(request):
    from .models import ExperimentResult

    results = (
        ExperimentResult.objects
        .filter(user=request.user)
        .select_related("experiment")
        .order_by("-completed_at")
    )
    return render(request, "laboratory/history.html", {"results": results})


@login_required
@require_POST
def submit_experiment(request, slug):
    """
    Reçoit la configuration de la paillasse (récipients + réactifs versés
    + volumes), la compare à la recette attendue de l'expérience, calcule
    les valeurs des indicateurs, sauvegarde le résultat et le renvoie en JSON.
    """
    experiment = get_object_or_404(Experiment, slug=slug, is_published=True)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Données invalides."}, status=400)

    containers = payload.get("containers", [])

    # --- Totaux versés, réactif par réactif ---
    actual_totals = {}
    last_reagent_name = None

    for container in containers:
        pours = container.get("pours", [])
        for pour in pours:
            name = pour.get("reagent")
            try:
                volume = float(pour.get("volume", 0))
            except (TypeError, ValueError):
                volume = 0
            if name:
                actual_totals[name] = actual_totals.get(name, 0) + volume
                last_reagent_name = name

    total_volume = sum(actual_totals.values())

    # --- Comparaison à la recette attendue (ExpectedReagentAmount) ---
    expected_qs = list(experiment.expected_reagents.select_related("reagent"))
    scores = []
    details = []

    for ea in expected_qs:
        actual = actual_totals.get(ea.reagent.name, 0)
        diff = abs(actual - ea.target_volume)
        within_tolerance = diff <= ea.tolerance

        if ea.target_volume > 0:
            proximity = max(0.0, 1 - diff / ea.target_volume)
        else:
            proximity = 1.0 if actual == 0 else 0.0

        scores.append(1.0 if within_tolerance else proximity)
        details.append({
            "reagent": ea.reagent.name,
            "target": ea.target_volume,
            "actual": round(actual, 1),
            "correct": within_tolerance,
        })

    if scores:
        overall_score = sum(scores) / len(scores)
    else:
        # Aucune recette définie pour cette expérience : on considère la
        # manipulation réussie dès qu'il y a eu une action sur la paillasse.
        overall_score = 1.0 if actual_totals else 0.0

    is_successful = overall_score >= 0.8

    # --- Couleur résultante : celle du dernier réactif versé ---
    result_color = "#94a3b8"
    if last_reagent_name:
        reagent_obj = Reagent.objects.filter(name=last_reagent_name).first()
        if reagent_obj and reagent_obj.color:
            result_color = reagent_obj.color

    # --- Calcul de chaque indicateur suivi pour cette expérience ---
    experiment_indicators = experiment.indicators.select_related("indicator")
    values_payload = {}

    for ei in experiment_indicators:
        indicator = ei.indicator
        name = indicator.name

        if name == "pH":
            primary = expected_qs[0] if expected_qs else None
            if primary and primary.target_volume > 0:
                actual = actual_totals.get(primary.reagent.name, 0)
                shift = (actual - primary.target_volume) / primary.target_volume * 4
                value = round(max(0.0, min(14.0, 7 + shift)), 1)
            else:
                value = 7.0 if is_successful else round(7 + (1 - overall_score) * 3, 1)

        elif name == "Volume versé":
            value = round(total_volume, 1)

        elif name == "Couleur de la solution":
            value = result_color

        elif indicator.value_type == "boolean":
            value = is_successful

        elif indicator.value_type == "color":
            value = result_color

        elif indicator.value_type == "number":
            # Approximation générique basée sur la précision du dosage réalisé
            value = round(overall_score * 100, 1)

        else:
            value = "Conforme" if is_successful else "À corriger"

        values_payload[str(indicator.id)] = {
            "name": name,
            "unit": indicator.unit,
            "value": value,
        }

    # --- Sauvegarde en base ---
    result = ExperimentResult.objects.create(
        experiment=experiment,
        user=request.user,
        is_successful=is_successful,
        summary=f"Score de précision : {round(overall_score * 100)}%",
    )
    for ei in experiment_indicators:
        indicator = ei.indicator
        ResultValue.objects.create(
            result=result,
            indicator=indicator,
            value=str(values_payload[str(indicator.id)]["value"]),
        )

    return JsonResponse({
        "is_successful": is_successful,
        "score": round(overall_score * 100),
        "indicators": values_payload,
        "details": details,
    })