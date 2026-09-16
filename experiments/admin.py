from django.contrib import admin
from .models import Experiment


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "level",
        "duration",
        "is_featured",
        "is_published",
    )

    list_filter = (
        "level",
        "is_featured",
        "is_published",
    )

    search_fields = (
        "title",
        "short_description",
    )

    prepopulated_fields = {
        "slug": ("title",),
    }
