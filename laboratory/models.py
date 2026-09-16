from django.conf import settings
from django.db import models
from experiments.models import Experiment


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
    icon = models.ImageField(upload_to="reagents/", blank=True, null=True)

    def __str__(self):
        return self.name


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