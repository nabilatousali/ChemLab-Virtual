from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

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
                leader=request.user,
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
        "is_leader": group.leader_id == request.user.id,
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

    if group.leader_id != request.user.id:
        messages.error(request, "Seul le chef du groupe peut inviter de nouveaux membres.")
        return redirect("groups:detail", slug=group.slug)

    if request.method == "POST":
        email = request.POST.get("email", "").strip()

        if not email:
            messages.error(request, "Indiquez une adresse e-mail.")
        else:
            try:
                user_to_invite = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                messages.error(
                    request,
                    f"Aucun compte inscrit sur la plateforme avec l'adresse « {email} ».",
                )
            else:
                if GroupMembership.objects.filter(group=group, user=user_to_invite).exists():
                    messages.info(request, f"{user_to_invite.username} est déjà membre de ce groupe.")
                else:
                    invitation, created = GroupInvitation.objects.get_or_create(
                        group=group,
                        invited_user=user_to_invite,
                        defaults={"invited_by": request.user},
                    )
                    if not created:
                        if invitation.status == "pending":
                            messages.info(request, f"{user_to_invite.username} a déjà une invitation en attente.")
                        else:
                            invitation.status = "pending"
                            invitation.invited_by = request.user
                            invitation.responded_at = None
                            invitation.save()
                            messages.success(request, f"Invitation envoyée à {user_to_invite.username}.")
                    else:
                        messages.success(request, f"Invitation envoyée à {user_to_invite.username}.")

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
        if _wants_json(request):
            return JsonResponse({"error": "Membre uniquement."}, status=403)
        messages.error(request, "Vous devez être membre de ce groupe pour discuter ici.")
        return redirect("groups:list")

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            message = GroupMessage.objects.create(
                group=group, sender=request.user, content=content
            )
            if _wants_json(request):
                return JsonResponse({"message": _serialize_message(message, request.user)})

    if _wants_json(request):
        return JsonResponse({"message": None})

    return redirect("groups:detail", slug=group.slug)


def _wants_json(request):
    return (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("accept", "")
    )


def _serialize_message(message, user):
    return {
        "id": message.id,
        "sender": message.sender.username,
        "content": message.content,
        "sent_at": message.sent_at.strftime("%d/%m %H:%M"),
        "mine": message.sender_id == user.id,
    }


@login_required
def group_messages_json(request, slug):
    """Derniers messages du chat pour le polling temps réel (membres uniquement)."""
    group, is_member = _get_group_and_membership(request, slug)

    if not is_member:
        return JsonResponse({"error": "Membre uniquement."}, status=403)

    try:
        after_id = int(request.GET.get("after", 0))
    except (TypeError, ValueError):
        after_id = 0

    messages_qs = group.messages.select_related("sender").filter(id__gt=after_id)
    return JsonResponse({
        "messages": [_serialize_message(m, request.user) for m in messages_qs],
    })


@login_required
@require_POST
def group_remove_member(request, slug, user_id):
    """Le chef retire un membre du groupe (ni lui-même, ni la direction)."""
    group, is_member = _get_group_and_membership(request, slug)

    if not is_member or group.leader_id != request.user.id:
        messages.error(request, "Seul le chef du groupe peut retirer un membre.")
        return redirect("groups:detail", slug=group.slug)

    if user_id == request.user.id:
        messages.error(request, "Pour quitter le groupe, utilisez le bouton « Quitter ».")
        return redirect("groups:detail", slug=group.slug)

    membership = GroupMembership.objects.filter(group=group, user_id=user_id).first()
    if membership is None:
        messages.error(request, "Cet utilisateur n'est pas membre du groupe.")
    else:
        username = membership.user.username
        membership.delete()
        messages.success(request, f"{username} a été retiré du groupe.")

    return redirect("groups:detail", slug=group.slug)


@login_required
@require_POST
def group_leave(request, slug):
    """Quitter le groupe. Si le chef part, la direction passe au membre le plus ancien."""
    group, is_member = _get_group_and_membership(request, slug)

    if not is_member:
        return redirect("groups:list")

    GroupMembership.objects.filter(group=group, user=request.user).delete()

    remaining = group.memberships.order_by("joined_at", "id")
    if not remaining.exists():
        group_name = group.name
        group.delete()
        messages.info(request, f"Le groupe « {group_name} » a été supprimé (plus aucun membre).")
        return redirect("groups:list")

    if group.leader_id == request.user.id:
        new_leader = remaining.first().user
        group.leader = new_leader
        group.save(update_fields=["leader"])
        messages.info(
            request,
            f"Vous avez quitté le groupe. {new_leader.username} en est désormais le chef.",
        )
    else:
        messages.info(request, "Vous avez quitté le groupe.")

    return redirect("groups:list")


@login_required
@require_POST
def group_transfer(request, slug):
    """Le chef transmet la direction à un autre membre."""
    group, is_member = _get_group_and_membership(request, slug)

    if not is_member or group.leader_id != request.user.id:
        messages.error(request, "Seul le chef du groupe peut transmettre la direction.")
        return redirect("groups:detail", slug=group.slug)

    username = request.POST.get("username", "").strip()
    target = GroupMembership.objects.filter(
        group=group, user__username=username
    ).select_related("user").first()

    if target is None:
        messages.error(request, "Choisissez un membre du groupe.")
    elif target.user_id == request.user.id:
        messages.error(request, "Vous êtes déjà le chef du groupe.")
    else:
        group.leader = target.user
        group.save(update_fields=["leader"])
        messages.success(
            request, f"{target.user.username} est désormais le chef du groupe."
        )

    return redirect("groups:detail", slug=group.slug)


@login_required
@require_POST
def group_delete(request, slug):
    """Le chef supprime définitivement le groupe."""
    group, is_member = _get_group_and_membership(request, slug)

    if not is_member or group.leader_id != request.user.id:
        messages.error(request, "Seul le chef du groupe peut le supprimer.")
        return redirect("groups:detail", slug=group.slug)

    group_name = group.name
    group.delete()
    messages.info(request, f"Le groupe « {group_name} » a été supprimé.")

    return redirect("groups:list")