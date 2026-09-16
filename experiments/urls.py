from django.urls import path

from . import views


app_name = "experiments"

urlpatterns = [
    path("", views.catalogue, name="catalogue"),
    path(
        "<slug:slug>/",
        views.detail,
        name="detail"
    ),
]
