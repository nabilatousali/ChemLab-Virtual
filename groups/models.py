from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from laboratory.models import ExperimentResult


class Group(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_groups",
    )
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="led_groups",
        help_text="Chef du groupe : invitations, retraits, transfert et suppression.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)[:100] or "groupe"
            slug = base_slug
            counter = 1
            while Group.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "user")

    def __str__(self):
        return f"{self.user} dans {self.group}"


class GroupInvitation(models.Model):
    """Invitation envoyée à un utilisateur déjà inscrit ; il peut l'accepter ou la refuser."""
    STATUS_CHOICES = [
        ("pending", "En attente"),
        ("accepted", "Acceptée"),
        ("declined", "Refusée"),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="invitations")
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="group_invitations",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_group_invitations",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("group", "invited_user")
        ordering = ["-created_at"]

    def accept(self):
        GroupMembership.objects.get_or_create(group=self.group, user=self.invited_user)
        self.status = "accepted"
        self.responded_at = timezone.now()
        self.save()

    def decline(self):
        self.status = "declined"
        self.responded_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.invited_user} invité dans {self.group} ({self.status})"


class SharedResult(models.Model):
    """Une expérience réalisée par un membre, partagée avec le groupe."""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="shared_results")
    result = models.ForeignKey(ExperimentResult, on_delete=models.CASCADE, related_name="shares")
    shared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-shared_at"]
        unique_together = ("group", "result")

    def __str__(self):
        return f"{self.result} partagé dans {self.group}"


class GroupMessage(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sent_at"]

    def __str__(self):
        return f"{self.sender} : {self.content[:30]}"