from django.db import models
from django.urls import reverse


class Experiment(models.Model):

    LEVELS = [
        ("easy", "Facile"),
        ("medium", "Intermédiaire"),
        ("advanced", "Avancé"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    short_description = models.TextField()
    description = models.TextField(blank=True)

    image = models.ImageField(
        upload_to="experiments/",
        blank=True,
        null=True
    )

    level = models.CharField(
        max_length=20,
        choices=LEVELS,
        default="easy"
    )

    duration = models.PositiveIntegerField(default=10)

    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse(
            "experiments:detail",
            kwargs={"slug": self.slug}
        )

