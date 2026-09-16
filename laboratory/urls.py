from django.urls import path

from . import views

app_name = "laboratory"

urlpatterns = [
    path("", views.home, name="home"),
    path("mes-experiences/", views.dashboard, name="dashboard"),
    path("laboratoire/<slug:slug>/", views.laboratory_workspace, name="workspace"),
]