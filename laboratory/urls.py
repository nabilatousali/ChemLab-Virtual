from django.urls import path

from . import views

app_name = "laboratory"

urlpatterns = [
    path("", views.home, name="home"),
    path("mes-experiences/", views.dashboard, name="dashboard"),
    path("historique/", views.history, name="history"),
    path("laboratoire/", views.laboratory_redirect, name="laboratory"),
    path("laboratoire/<slug:slug>/", views.laboratory_workspace, name="workspace"),
    path("laboratoire/<slug:slug>/resultat/", views.submit_experiment, name="submit_result"),
]