from django.db import models
from django.templatetags.static import static
from django.urls import reverse


# Images statiques encore inutilisées, attribuées une seule fois :
# chaque expérience a sa propre couverture, sans doublon.
COVER_IMAGES = {
    "dosage-acido-basique-etalonnage-hcl": "pexels-anntarazevich-8392790.jpg",
    "dosage-complexometrique-du-calcium-et-du-magnesium": "pexels-artempodrez-8533087.jpg",
    "dosage-de-laspirine-dans-un-comprime": "pexels-dubart-6608507.jpg",
    "dosage-doxydoreduction-manganimetrie": "pexels-karola-g-8539952.jpg",
    "extraction-des-huiles-essentielles": "pexels-kindelmedia-8325708.jpg",
    "extraction-liquide-liquide-de-colorants-de-fruits": "pexels-mikhail-nilov-8850985.jpg",
    "preparation-de-solutions": "pexels-mikhail-nilov-8850993.jpg",
    "production-de-savon-liquide-detergent": "pexels-polina-tankilevitch-3735703.jpg",
    "production-dhuile-vegetale-coco-arachide": "pexels-ron-lach-10187144.jpg",
    "production-et-dosage-de-leau-de-javel": "pexels-ron-lach-10187996.jpg",
    "synthese-de-laspirine": "pexels-ivan-s-9629694.jpg",
    "synthese-du-savon-saponification": "pexels-karola-g-8539949.jpg",
}

DEFAULT_COVER_IMAGE = "images/chemlab-experiments.jpg"


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

    @property
    def cover_image(self):
        """URL de l'image de couverture : upload admin en priorité,
        sinon l'image statique dédiée à l'expérience, sinon le visuel générique."""
        if self.image:
            return self.image.url
        filename = COVER_IMAGES.get(self.slug)
        if filename:
            return static(f"images/{filename}")
        return static(DEFAULT_COVER_IMAGE)

    def get_absolute_url(self):
        return reverse(
            "experiments:detail",
            kwargs={"slug": self.slug}
        )

