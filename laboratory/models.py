from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from experiments.models import Experiment


# Pictogrammes SGH reconnus par la plateforme (affichés dans le labo).
GHS_PICTOGRAMS = [
    ("GHS01", "Explosif"),
    ("GHS02", "Inflammable"),
    ("GHS03", "Oxydant (comburant)"),
    ("GHS04", "Gaz sous pression"),
    ("GHS05", "Corrosif"),
    ("GHS06", "Toxique"),
    ("GHS07", "Irritant / Nocif"),
    ("GHS08", "Danger pour la santé"),
    ("GHS09", "Danger pour l'environnement"),
]

GHS_LABELS = dict(GHS_PICTOGRAMS)

# Pictogrammes qui déclenchent une alerte bloquante avant versement.
GHS_DANGER_CODES = frozenset({"GHS01", "GHS02", "GHS03", "GHS05", "GHS06", "GHS08"})


def parse_hazard_codes(value):
    """Normalise une liste de codes SGH (chaîne « GHS05,GHS07 » ou liste)."""
    if not value:
        return []
    if isinstance(value, str):
        value = value.split(",")
    codes = []
    for code in value:
        code = str(code).strip().upper()
        if code and code not in codes:
            codes.append(code)
    return codes


class Material(models.Model):
    """Outil réutilisable, jamais consommé : bécher, erlenmeyer, pipette..."""
    name = models.CharField(max_length=100)
    icon = models.ImageField(upload_to="materials/", blank=True, null=True)

    def __str__(self):
        return self.name


class Reagent(models.Model):
    """Produit chimique manipulable : solution acide, nitrate d'argent..."""
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, blank=True, help_text="Couleur d'affichage, ex: #3498db")
    concentration = models.CharField(max_length=50, blank=True, help_text="Ex: 0.1 mol/L")
    ph = models.FloatField(
        null=True,
        blank=True,
        help_text="pH de la solution telle que stockée (optionnel, pour le laboratoire libre)",
    )
    hazards = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Pictogrammes SGH séparés par des virgules, ex : GHS05,GHS07",
    )
    safety_advice = models.TextField(
        blank=True,
        default="",
        help_text="Conseils de manipulation affichés avant versement.",
    )
    incompatible_with = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=True,
        help_text="Réactifs à ne pas mélanger avec celui-ci (alerte de sécurité).",
    )
    icon = models.ImageField(upload_to="reagents/", blank=True, null=True)

    def __str__(self):
        return self.name

    def clean(self):
        valid = set(GHS_LABELS)
        unknown = [c for c in parse_hazard_codes(self.hazards) if c not in valid]
        if unknown:
            raise ValidationError(
                {"hazards": f"Codes SGH inconnus : {', '.join(unknown)}."}
            )

    @property
    def hazard_list(self):
        return parse_hazard_codes(self.hazards)

    @property
    def hazard_badges(self):
        """Couples (code, est_dangereux) pour l'affichage des pastilles."""
        return [(code, code in GHS_DANGER_CODES) for code in self.hazard_list]

    @property
    def has_danger(self):
        return any(code in GHS_DANGER_CODES for code in self.hazard_list)


class ExperimentMaterial(models.Model):
    """Le matériel proposé pour une expérience donnée."""
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="materials")
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.experiment.title} - {self.material.name}"


class ExperimentReagent(models.Model):
    """Les réactifs proposés pour une expérience donnée."""
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="reagents")
    reagent = models.ForeignKey(Reagent, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.experiment.title} - {self.reagent.name}"


class ProtocolStep(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="steps")
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=150)
    description = models.TextField()

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"{self.experiment.title} - étape {self.number}"


# --- Système de bilan flexible ---

class Indicator(models.Model):
    VALUE_TYPES = [
        ("number", "Nombre"),
        ("text", "Texte"),
        ("boolean", "Oui / Non"),
        ("color", "Couleur"),
    ]
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20, blank=True)
    value_type = models.CharField(max_length=20, choices=VALUE_TYPES)

    def __str__(self):
        return self.name


class ReactionType(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    default_indicators = models.ManyToManyField(Indicator, blank=True, related_name="reaction_types")

    def __str__(self):
        return self.name


class ExperimentConfig(models.Model):
    experiment = models.OneToOneField(Experiment, on_delete=models.CASCADE, related_name="lab_config")
    reaction_type = models.ForeignKey(ReactionType, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Configuration - {self.experiment.title}"


class ExperimentIndicator(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="indicators")
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = ("experiment", "indicator")

    def __str__(self):
        return f"{self.experiment.title} - {self.indicator.name}"


class ExperimentResult(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="results")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=True)
    summary = models.TextField(blank=True)

    def __str__(self):
        return f"{self.experiment.title} - {self.user}"


class ResultValue(models.Model):
    result = models.ForeignKey(ExperimentResult, on_delete=models.CASCADE, related_name="values")
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.indicator.name} = {self.value}"


class ExpectedReagentAmount(models.Model):
    """La quantité correcte d'un réactif à verser pour une expérience donnée."""
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="expected_reagents")
    reagent = models.ForeignKey(Reagent, on_delete=models.CASCADE)
    target_volume = models.FloatField(help_text="Volume correct attendu, en mL")
    tolerance = models.FloatField(default=1.0, help_text="Marge d'erreur acceptée, en mL")

    class Meta:
        unique_together = ("experiment", "reagent")

    def __str__(self):
        return f"{self.experiment.title} - {self.reagent.name} : {self.target_volume} mL"


class UserBenchReagent(models.Model):
    """Réactif de la « paillasse libre », ajouté par un utilisateur via PubChem.

    Ce modèle est séparé de ``Reagent`` (géré par l'administrateur et lié
    aux expériences notées) afin de ne pas perturber le moteur de scoring
    des travaux pratiques. PubChem fournit uniquement les métadonnées du
    composé ; le calcul des grandeurs est assuré par l'application.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bench_reagents",
    )
    name = models.CharField(max_length=250)
    pubchem_cid = models.PositiveIntegerField(null=True, blank=True)
    molecular_formula = models.CharField(max_length=100, blank=True)
    molecular_weight = models.FloatField(null=True, blank=True, help_text="Masse molaire en g/mol")
    canonical_smiles = models.TextField(blank=True)
    isomeric_smiles = models.TextField(blank=True)
    inchi = models.TextField(blank=True)
    inchikey = models.CharField(max_length=30, blank=True)
    synonyms = models.TextField(blank=True, help_text="Synonymes séparés par des virgules")
    image_url = models.URLField(blank=True)
    color = models.CharField(max_length=20, blank=True, default="#3498db")

    # Données de danger PubChem (GHS), récupérées une seule fois à l'import
    # du composé puis stockées : les alertes restent disponibles hors-ligne.
    hazards = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Pictogrammes SGH séparés par des virgules, ex : GHS05,GHS07",
    )
    hazard_statements = models.TextField(
        blank=True,
        default="",
        help_text="Mentions de danger PubChem (ex : H314: ...), séparées par « ; ».",
    )

    volume_ml = models.FloatField(default=0.0, help_text="Volume choisi par l'utilisateur, en mL")
    concentration = models.FloatField(
        null=True,
        blank=True,
        help_text="Concentration en mol/L (optionnelle)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("user", "pubchem_cid")

    def __str__(self):
        return f"{self.name} — {self.user.username}"

    @property
    def hazard_list(self):
        return parse_hazard_codes(self.hazards)

    @property
    def hazard_badges(self):
        """Couples (code, est_dangereux) pour l'affichage des pastilles."""
        return [(code, code in GHS_DANGER_CODES) for code in self.hazard_list]

    @property
    def has_danger(self):
        return any(code in GHS_DANGER_CODES for code in self.hazard_list)