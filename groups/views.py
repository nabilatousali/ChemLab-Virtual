from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from laboratory.models import ExperimentResult
from .models import Group, GroupMembership, GroupInvitation, SharedResult, GroupMessage


@login_required
def group_list(request):
    groups = Group.objects.filter(memberships__user=request.user).distinct()
    pending_invitations = GroupInvitation.objects.filter(
        invited_user=request.user, status="pending"
    ).select_related("group", "invited_by")

    context = {
        "groups": groups,
        "pending_invitations": pending_invitations,
    }
    return render(request, "groups/group_list.html", context)


@login_required
def group_create(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if not name:
            messages.error(request, "Le nom du groupe est obligatoire.")
        else:
            group = Group.objects.create(
                name=name,
                description=description,
                created_by=request.user,
            )
            GroupMembership.objects.create(group=group, user=request.user)
            messages.success(request, "Groupe créé avec succès.")
            return redirect("groups:detail", slug=group.slug)

    return render(request, "groups/group_create.html")


def _get_group_and_membership(request, slug):
    group = get_object_or_404(Group, slug=slug)
    is_member = GroupMembership.objects.filter(group=group, user=request.user).exists()
    return group, is_member


@login_required
def group_detail(request, slug):
    group, is_member = _get_group_and_membership(request, slug)

    if not is_member:
        messages.error(request, "Vous devez être membre de ce groupe pour y accéder.")
        return redirect("groups:list")

    context = {
        "group": group,
        "memberships": group.memberships.select_related("user").order_by("joined_at"),
        "pending_invitations_sent": group.invitations.filter(status="pending").select_related("invited_user"),
        "shared_results": group.shared_results.select_related(
            "result", "result__experiment", "shared_by"
        ),
        "chat_messages": group.messages.select_related("sender"),
        "my_results": ExperimentResult.objects.filter(user=request.user)
        .select_related("experiment")
        .order_by("-completed_at"),
    }
    return render(request, "groups/group_detail.html", context)


@login_required
def group_invite_member(request, slug):
    group, is_member = _get_group_and_membership(request, slug)

    if not is_member:
        messages.error(request, "Vous devez être membre de ce groupe pour y inviter quelqu'un.")
        return redirect("groups:list")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()

        if not username:
            messages.error(request, "Indiquez un nom d'utilisateur.")
        else:
            try:
                user_to_invite = User.objects.get(username=username)
            except User.DoesNotExist:
                messages.error(
                    request,
                    f"Aucun utilisateur inscrit sur la plateforme avec le nom « {username} ».",
                )
            else:
                if GroupMembership.objects.filter(group=group, user=user_to_invite).exists():
                    messages.info(request, f"{username} est déjà membre de ce groupe.")
                else:
                    invitation, created = GroupInvitation.objects.get_or_create(
                        group=group,
                        invited_user=user_to_invite,
                        defaults={"invited_by": request.user},
                    )
                    if not created:
                        if invitation.status == "pending":
                            messages.info(request, f"{username} a déjà une invitation en attente.")
                        else:
                            invitation.status = "pending"
                            invitation.invited_by = request.user
                            invitation.responded_at = None
                            invitation.save()
                            messages.success(request, f"Invitation envoyée à {username}.")
                    else:
                        messages.success(request, f"Invitation envoyée à {username}.")

    return redirect("groups:detail", slug=group.slug)


@login_required
def respond_invitation(request, invitation_id):
    invitation = get_object_or_404(
        GroupInvitation, id=invitation_id, invited_user=request.user, status="pending"
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "accept":
            invitation.accept()
            messages.success(request, f"Vous avez rejoint le groupe « {invitation.group.name} ».")
            return redirect("groups:detail", slug=invitation.group.slug)

        elif action == "decline":
            invitation.decline()
            messages.info(request, f"Invitation refusée pour « {invitation.group.name} ».")

    return redirect("groups:list")


@login_required
def group_share_result(request, slug):
    group, is_member = _get_group_and_membership(request, slug)

    if not is_member:
        messages.error(request, "Vous devez être membre de ce groupe pour y partager un résultat.")
        return redirect("groups:list")

    if request.method == "POST":
        result_id = request.POST.get("result_id")
        result = get_object_or_404(ExperimentResult, id=result_id, user=request.user)
        _, created = SharedResult.objects.get_or_create(
            group=group, result=result, shared_by=request.user
        )
        if created:
            messages.success(request, "Expérience partagée avec le groupe.")
        else:
            messages.info(request, "Cette expérience est déjà partagée dans ce groupe.")

    return redirect("groups:detail", slug=group.slug)


@login_required
def group_send_message(request, slug):
    group, is_member = _get_group_and_membership(request, slug)

    if not is_member:
        messages.error(request, "Vous devez être membre de ce groupe pour discuter ici.")
        return redirect("groups:list")

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            GroupMessage.objects.create(group=group, sender=request.user, content=content)

    return redirect("groups:detail", slug=group.slug)