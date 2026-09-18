
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect, render, reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode, urlsafe_base64_encode
from django.conf import settings

from .forms import LoginForm, RegisterForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("laboratory:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            send_activation_email(request, user)
            messages.info(
                request,
                "Compte créé ! Vérifiez votre boîte e-mail pour l'activer "
                "avant de vous connecter.",
            )
            return redirect("accounts:login")

    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def send_activation_email(request, user):
    """Envoie le lien d'activation (console e-mail en local, SMTP en prod)."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    activation_url = request.build_absolute_uri(
        reverse("accounts:activate", kwargs={"uidb64": uid, "token": token})
    )
    send_mail(
        "Activez votre compte ChemLab Virtual",
        (
            f"Bonjour {user.first_name or user.username},\n\n"
            "Bienvenue sur ChemLab Virtual ! Cliquez sur le lien ci-dessous "
            "pour activer votre compte :\n\n"
            f"{activation_url}\n\n"
            "Si vous n'êtes pas à l'origine de cette inscription, "
            "ignorez cet e-mail."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


def activate_view(request, uidb64, token):
    """Active le compte via le lien reçu par e-mail, puis connecte."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save(update_fields=["is_active"])
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Votre compte est activé, bienvenue !")
        return redirect("laboratory:dashboard")

    messages.error(request, "Ce lien d'activation est invalide ou a expiré.")
    return redirect("accounts:login")


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