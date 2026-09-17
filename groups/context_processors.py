from .models import GroupInvitation


def pending_invitations_count(request):
    if request.user.is_authenticated:
        count = GroupInvitation.objects.filter(
            invited_user=request.user, status="pending"
        ).count()
    else:
        count = 0

    return {"pending_invitations_count": count}