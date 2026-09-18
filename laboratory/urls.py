from django.urls import path

from . import views

app_name = "laboratory"

urlpatterns = [
    path("", views.home, name="home"),
    path("mes-experiences/", views.dashboard, name="dashboard"),
    path("historique/", views.history, name="history"),
    path("laboratoire/", views.free_laboratory, name="laboratory"),
    path("laboratoire/analyser/", views.analyze_mixture, name="analyze_mixture"),
    path("laboratoire/<slug:slug>/", views.laboratory_workspace, name="workspace"),
    path("laboratoire/<slug:slug>/resultat/", views.submit_experiment, name="submit_result"),
    path("paillasse/", views.bench_view, name="bench"),
    path("paillasse/ajouter/<int:cid>/", views.bench_add, name="bench_add"),
    path("paillasse/retirer/<int:pk>/", views.bench_remove, name="bench_remove"),
    path("paillasse/simuler/", views.bench_simulate, name="bench_simulate"),
]