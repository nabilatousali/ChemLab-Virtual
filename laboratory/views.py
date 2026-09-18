import json
import math

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from experiments.models import Experiment
from .models import (
    GHS_DANGER_CODES,
    GHS_LABELS,
    Material,
    Reagent,
    ExperimentResult,
    ResultValue,
    UserBenchReagent,
)
from .services import pubchem


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
def free_laboratory(request):
    """Laboratoire libre : tout le catalogue (matériel + réactifs),
    sans expérience imposée ni protocole. Accessible directement
    depuis l'onglet « Laboratoire » de la navbar."""
    context = {
        "materials": Material.objects.order_by("name"),
        "reagents": Reagent.objects.prefetch_related("incompatible_with").order_by("name"),
        "bench_reagents": UserBenchReagent.objects.filter(user=request.user).order_by("name"),
        "ghs_labels": GHS_LABELS,
    }
    return render(request, "laboratory/free_lab.html", context)


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


# =====================================================================
# Paillasse libre (intégration PubChem)
# =====================================================================

_REAGENT_PALETTE = [
    "#2563eb", "#0d9488", "#d97706", "#7c3aed",
    "#dc2626", "#0891b2", "#db2777", "#65a30d",
]


def _default_reagent_color(cid):
    return _REAGENT_PALETTE[cid % len(_REAGENT_PALETTE)]


def _hex_to_rgb(value):
    value = (value or "").lstrip("#")
    if len(value) != 6:
        return (52, 152, 219)
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (52, 152, 219)


def _rgb_to_hex(rgb):
    parts = (max(0, min(255, int(round(channel)))) for channel in rgb)
    return "#{:02x}{:02x}{:02x}".format(*parts)


def _search_context(query):
    """Interroge PubChem et traduit les erreurs en messages utilisateurs."""
    if len(query) > 100:
        return {"search_error": "La recherche ne peut pas dépasser 100 caractères."}
    try:
        candidates = pubchem.search_compounds(query)
        if not candidates:
            return {"search_error": "Aucun composé trouvé pour ce nom dans PubChem."}
        return {"candidates": candidates}
    except pubchem.PubChemNotFound:
        return {"search_error": "Aucun composé trouvé pour ce nom dans PubChem."}
    except pubchem.PubChemRateLimited:
        return {
            "search_error": "PubChem reçoit trop de requêtes en ce moment. "
            "Réessayez dans quelques instants."
        }
    except pubchem.PubChemError as exc:
        return {
            "search_error": f"PubChem est momentanément indisponible ({exc}). Réessayez plus tard."
        }


@login_required
def bench_view(request):
    """Paillasse libre : recherche PubChem + réactifs de l'utilisateur."""
    context = {"reagents": UserBenchReagent.objects.filter(user=request.user)}

    query = (request.GET.get("q") or "").strip()
    if query:
        context["query"] = query
        context.update(_search_context(query))

    return render(request, "laboratory/bench.html", context)


@login_required
@require_POST
def bench_add(request, cid):
    """Ajoute un composé PubChem à la paillasse de l'utilisateur connecté."""
    if UserBenchReagent.objects.filter(user=request.user, pubchem_cid=cid).exists():
        messages.error(request, "Ce réactif est déjà présent dans votre paillasse.")
        return redirect("laboratory:bench")

    try:
        details = pubchem.get_compound_details(cid)
    except pubchem.PubChemNotFound:
        messages.error(request, "Ce composé n'existe pas dans PubChem.")
        return redirect("laboratory:bench")
    except (pubchem.PubChemRateLimited, pubchem.PubChemError) as exc:
        messages.error(request, f"Impossible de récupérer les données PubChem ({exc}).")
        return redirect("laboratory:bench")

    # Dangers GHS récupérés une seule fois puis stockés : les alertes
    # restent disponibles hors-ligne. Non bloquant en cas d'échec.
    try:
        ghs = pubchem.get_ghs_data(cid)
    except (pubchem.PubChemRateLimited, pubchem.PubChemError, pubchem.PubChemNotFound):
        ghs = {"pictograms": [], "statements": []}

    UserBenchReagent.objects.create(
        user=request.user,
        name=details["name"] or f"Composé PubChem #{cid}",
        pubchem_cid=cid,
        molecular_formula=details["formula"],
        molecular_weight=details["weight"],
        canonical_smiles=details["canonical_smiles"],
        isomeric_smiles=details["isomeric_smiles"],
        inchi=details["inchi"],
        inchikey=details["inchikey"],
        synonyms=", ".join(details["synonyms"]),
        image_url=details["image_url"],
        color=_default_reagent_color(cid),
        hazards=",".join(ghs["pictograms"]),
        hazard_statements="; ".join(ghs["statements"]),
    )
    messages.success(request, f"« {details['name'] or cid} » a été ajouté à votre paillasse.")
    if not ghs["pictograms"]:
        messages.info(
            request,
            "PubChem ne signale aucun pictogramme de danger pour ce composé.",
        )
    return redirect("laboratory:bench")


@login_required
@require_POST
def bench_remove(request, pk):
    reagent = get_object_or_404(UserBenchReagent, pk=pk, user=request.user)
    name = reagent.name
    reagent.delete()
    messages.success(request, f"« {name} » retiré de votre paillasse.")
    return redirect("laboratory:bench")


@login_required
@require_POST
def bench_simulate(request):
    """Calcule les grandeurs physico-chimiques dérivées des apports choisis.

    Le moteur reste l'application Django : PubChem n'a fourni que les
    propriétés de chaque composé (masse molaire, formule...). Les volumes
    et concentrations sont saisis par l'utilisateur sur sa paillasse.
    """
    reagents = list(UserBenchReagent.objects.filter(user=request.user))
    computed = []
    warnings = []

    total_volume = 0.0
    total_amount = 0.0   # mol
    total_mass = 0.0     # g
    has_amount = False
    mixed_rgb = [0.0, 0.0, 0.0]
    mix_volume = 0.0

    for reagent in reagents:
        raw_volume = request.POST.get(f"volume_{reagent.pk}", "0")
        raw_concentration = request.POST.get(f"conc_{reagent.pk}", "").strip()

        try:
            volume = max(0.0, float(raw_volume))
        except (TypeError, ValueError):
            warnings.append(f"Volume invalide pour « {reagent.name} » ; ignoré.")
            volume = 0.0

        concentration = None
        if raw_concentration:
            try:
                concentration = max(0.0, float(raw_concentration))
            except (TypeError, ValueError):
                warnings.append(
                    f"Concentration invalide pour « {reagent.name} » ; ignorée."
                )

        reagent.volume_ml = volume
        reagent.concentration = concentration
        reagent.save()

        amount = None   # mol : n = C × V
        mass = None     # g   : m = n × M
        if concentration is not None and volume > 0:
            amount = round(concentration * volume / 1000.0, 6)
            has_amount = True
            total_amount += amount
            if reagent.molecular_weight:
                mass = round(amount * reagent.molecular_weight, 4)
                total_mass += mass

        total_volume += volume

        if volume > 0:
            rgb = _hex_to_rgb(reagent.color)
            for i in range(3):
                mixed_rgb[i] += rgb[i] * volume
            mix_volume += volume

        computed.append({
            "reagent": reagent,
            "volume": round(volume, 1),
            "concentration": concentration,
            "amount": amount,
            "mass": mass,
        })

    mixed_color = (
        _rgb_to_hex(tuple(channel / mix_volume for channel in mixed_rgb))
        if mix_volume > 0
        else "#94a3b8"
    )

    context = {
        "reagents": reagents,
        "bench_results": {
            "total_volume": round(total_volume, 1),
            "total_amount": round(total_amount, 4),
            "total_mass": round(total_mass, 2),
            "has_amount": has_amount,
            "mixed_color": mixed_color,
            "computed": computed,
            "warnings": warnings,
        },
    }
    return render(request, "laboratory/bench.html", context)


# =====================================================================
# Laboratoire libre : analyse d'un mélange sans protocole
# =====================================================================

# Un réactif sans couleur renseignée est traité comme incolore : il
# dilue la couleur du mélange au lieu de la teinter.
_COLORLESS_RGB = (244, 250, 251)


@login_required
@require_POST
def analyze_mixture(request):
    """Analyse un mélange libre et renvoie les grandeurs de base en JSON :
    volume total, couleur mélangée, pH estimé et composition détaillée.

    Le pH est une estimation pédagogique : moyenne des concentrations
    en ions H+ ([H+] = 10^-pH) pondérée par les volumes. Les réactifs
    sans pH renseigné sont comptés comme neutres (signalés en avertissement).
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Données invalides."}, status=400)

    totals = {}
    for container in payload.get("containers", []):
        for pour in container.get("pours", []):
            name = pour.get("reagent")
            try:
                volume = float(pour.get("volume", 0))
            except (TypeError, ValueError):
                volume = 0
            if name and volume > 0:
                totals[name] = totals.get(name, 0) + volume

    raw_total = sum(totals.values())
    if raw_total <= 0:
        return JsonResponse(
            {"error": "Versez au moins un réactif dans un récipient avant d'analyser."},
            status=400,
        )

    catalog = {
        r.name: r
        for r in Reagent.objects.filter(name__in=list(totals)).prefetch_related(
            "incompatible_with"
        )
    }
    # Réactifs personnels de la paillasse : reconnus par leur couleur,
    # sans pH (comptés comme neutres).
    bench_stock = {
        r.name: r
        for r in UserBenchReagent.objects.filter(
            user=request.user, name__in=list(totals)
        )
    }

    mixed_rgb = [0.0, 0.0, 0.0]
    acidity = 0.0  # somme des [H+] × volumes
    unknown_reagents = []
    unknown_ph = []
    bench_unknown_ph = []
    composition = []

    for name, volume in sorted(totals.items(), key=lambda item: -item[1]):
        reagent = catalog.get(name)
        bench_reagent = bench_stock.get(name) if reagent is None else None

        if reagent is not None:
            color = reagent.color or ""
        elif bench_reagent is not None:
            color = bench_reagent.color or ""
        else:
            color = ""
        rgb = _hex_to_rgb(color) if color else _COLORLESS_RGB
        for i in range(3):
            mixed_rgb[i] += rgb[i] * volume

        if reagent is not None and reagent.ph is not None:
            hydrogen = 10.0 ** (-reagent.ph)
        else:
            hydrogen = 1e-7  # neutre par défaut
            if reagent is None and bench_reagent is None:
                unknown_reagents.append(name)
            elif bench_reagent is not None:
                bench_unknown_ph.append(name)
            else:
                unknown_ph.append(name)
        acidity += hydrogen * volume

        composition.append({
            "reagent": name,
            "volume": round(volume, 1),
            "percent": round(volume / raw_total * 100, 1),
            "color": _rgb_to_hex(rgb),
        })

    mixed_color = _rgb_to_hex(tuple(channel / raw_total for channel in mixed_rgb))
    ph_value = round(-math.log10(acidity / raw_total), 1)

    warnings = []
    for name in unknown_reagents:
        warnings.append(f"« {name} » est inconnu du catalogue : compté comme neutre et incolore.")
    for name in unknown_ph:
        warnings.append(f"pH de « {name} » non renseigné : compté comme neutre.")
    for name in bench_unknown_ph:
        warnings.append(f"« {name} » vient de votre paillasse (sans pH) : compté comme neutre.")

    # --- Sécurité du mélange : pictogrammes, conseils, incompatibilités ---
    poured_names = [item["reagent"] for item in composition]

    safety_codes = []
    for item in composition:
        reagent = catalog.get(item["reagent"])
        if reagent is None:
            reagent = bench_stock.get(item["reagent"])
        for code in reagent.hazard_list if reagent else []:
            if code not in safety_codes:
                safety_codes.append(code)

    safety_advice = [
        {"reagent": name, "text": catalog[name].safety_advice}
        for name in poured_names
        if name in catalog and catalog[name].safety_advice
    ]

    incompatible_map = {
        name: {other.name for other in reagent.incompatible_with.all()}
        for name, reagent in catalog.items()
    }
    safety_warnings = []
    for position, first in enumerate(poured_names):
        for second in poured_names[position + 1:]:
            if second in incompatible_map.get(first, set()):
                safety_warnings.append(
                    f"« {first} » est incompatible avec « {second} » : "
                    "risque de réaction dangereuse, ne pas mélanger."
                )

    safety = {
        "pictograms": [
            {"code": code, "label": GHS_LABELS.get(code, code)}
            for code in safety_codes
        ],
        "has_danger": any(code in GHS_DANGER_CODES for code in safety_codes),
        "warnings": safety_warnings,
        "advice": safety_advice,
    }

    return JsonResponse({
        "total_volume": round(raw_total, 1),
        "mixed_color": mixed_color,
        "ph": ph_value,
        "dominant": composition[0]["reagent"],
        "indicators": {
            "volume": {"name": "Volume total", "unit": " mL", "value": round(raw_total, 1)},
            "color": {"name": "Couleur du mélange", "unit": "", "value": mixed_color},
            "ph": {"name": "pH estimé", "unit": "", "value": ph_value},
            "count": {"name": "Réactifs mélangés", "unit": "", "value": len(composition)},
        },
        "composition": composition,
        "warnings": warnings,
        "safety": safety,
    })