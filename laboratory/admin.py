from django import forms as django_forms
from django.contrib import admin

from .models import (
    ExpectedReagentAmount,
    ExperimentConfig,
    ExperimentIndicator,
    ExperimentMaterial,
    ExperimentReagent,
    ExperimentResult,
    GHS_PICTOGRAMS,
    Indicator,
    Material,
    ProtocolStep,
    ReactionType,
    Reagent,
    ResultValue,
    UserBenchReagent,
)


class ReagentAdminForm(django_forms.ModelForm):
    """Pictogrammes SGH en cases à cocher (stockés en CSV)."""

    hazard_checks = django_forms.MultipleChoiceField(
        choices=GHS_PICTOGRAMS,
        required=False,
        widget=django_forms.CheckboxSelectMultiple,
        label="Pictogrammes SGH",
    )

    class Meta:
        model = Reagent
        exclude = ("hazards",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["hazard_checks"].initial = self.instance.hazard_list

    def save(self, commit=True):
        self.instance.hazards = ",".join(self.cleaned_data.get("hazard_checks") or [])
        return super().save(commit)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Reagent)
class ReagentAdmin(admin.ModelAdmin):
    form = ReagentAdminForm
    list_display = ("name", "concentration", "color", "ph")
    search_fields = ("name", "concentration")
    filter_horizontal = ("incompatible_with",)


@admin.register(ExperimentMaterial)
class ExperimentMaterialAdmin(admin.ModelAdmin):
    list_display = ("experiment", "material", "order")
    list_filter = ("experiment",)
    search_fields = ("experiment__title", "material__name")
    ordering = ("experiment", "order")


@admin.register(ExperimentReagent)
class ExperimentReagentAdmin(admin.ModelAdmin):
    list_display = ("experiment", "reagent", "order")
    list_filter = ("experiment",)
    search_fields = ("experiment__title", "reagent__name")
    ordering = ("experiment", "order")


@admin.register(ProtocolStep)
class ProtocolStepAdmin(admin.ModelAdmin):
    list_display = ("experiment", "number", "title")
    list_filter = ("experiment",)
    search_fields = ("title", "description", "experiment__title")
    ordering = ("experiment", "number")


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ("name", "unit", "value_type")
    list_filter = ("value_type",)
    search_fields = ("name",)


@admin.register(ReactionType)
class ReactionTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(ExperimentConfig)
class ExperimentConfigAdmin(admin.ModelAdmin):
    list_display = ("experiment", "reaction_type")
    list_filter = ("reaction_type",)
    search_fields = ("experiment__title",)


@admin.register(ExperimentIndicator)
class ExperimentIndicatorAdmin(admin.ModelAdmin):
    list_display = ("experiment", "indicator", "order")
    list_filter = ("experiment",)
    ordering = ("experiment", "order")


class ResultValueInline(admin.TabularInline):
    model = ResultValue
    extra = 0


@admin.register(ExperimentResult)
class ExperimentResultAdmin(admin.ModelAdmin):
    list_display = ("experiment", "user", "is_successful", "completed_at")
    list_filter = ("is_successful", "experiment", "completed_at")
    search_fields = ("experiment__title", "user__username", "summary")
    date_hierarchy = "completed_at"
    inlines = [ResultValueInline]


@admin.register(ResultValue)
class ResultValueAdmin(admin.ModelAdmin):
    list_display = ("result", "indicator", "value")
    search_fields = ("indicator__name", "value")


@admin.register(ExpectedReagentAmount)
class ExpectedReagentAmountAdmin(admin.ModelAdmin):
    list_display = ("experiment", "reagent", "target_volume", "tolerance")
    list_filter = ("experiment",)
    search_fields = ("experiment__title", "reagent__name")


@admin.register(UserBenchReagent)
class UserBenchReagentAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "pubchem_cid", "molecular_formula", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "user__username", "pubchem_cid")
