from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import LoginForm, RegisterForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("laboratory:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()

            # Sécurité : le compte doit être actif dès l'inscription.
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active"])

            # Connexion automatique, sans e-mail de vérification.
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Compte créé, bienvenue sur ChemLab Virtual !")
            return redirect("laboratory:dashboard")

    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("laboratory:dashboard")

    if request.method == "POST":
        form = LoginForm(request.POST, request=request)

        if form.is_valid():
            user = form.user
            login(request, user)

            # Anti open-redirect : on ne suit que les URL locales.
            next_url = request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)

            return redirect("laboratory:dashboard")

    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("laboratory:home")


@login_required
def profile_view(request):
    from laboratory.models import ExperimentResult

    results = (
        ExperimentResult.objects
        .filter(user=request.user)
        .select_related("experiment")
        .order_by("-completed_at")
    )

    total = results.count()
    succeeded = results.filter(is_successful=True).count()
    scores = [
        int(r.summary.split(":")[-1].replace("%", "").strip())
        for r in results
        if ":" in r.summary
    ]
    average = round(sum(scores) / len(scores)) if scores else None

    context = {
        "results": results,
        "total_results": total,
        "successful_results": succeeded,
        "average_score": average,
    }
    return render(request, "accounts/profile.html", context)
