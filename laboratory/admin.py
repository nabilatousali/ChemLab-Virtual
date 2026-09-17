from django.contrib import admin
from .models import (
    Material,
    Reagent,
    ExperimentMaterial,
    ExperimentReagent,
    ProtocolStep,
    Indicator,
    ReactionType,
    ExperimentConfig,
    ExperimentIndicator,
    ExperimentResult,
    ResultValue,
    ExpectedReagentAmount,
)

admin.site.register(Material)
admin.site.register(Reagent)
admin.site.register(Indicator)
admin.site.register(ReactionType)
admin.site.register(ExperimentConfig)
admin.site.register(ExperimentResult)
admin.site.register(ExperimentMaterial)
admin.site.register(ExperimentReagent)
admin.site.register(ProtocolStep)
admin.site.register(ExperimentIndicator)
admin.site.register(ResultValue)
admin.site.register(ExpectedReagentAmount)