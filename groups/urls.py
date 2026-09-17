from django.urls import path

from . import views

app_name = "groups"

urlpatterns = [
    path("", views.group_list, name="list"),
    path("creer/", views.group_create, name="create"),
    path("<slug:slug>/", views.group_detail, name="detail"),
    path("<slug:slug>/inviter/", views.group_invite_member, name="invite_member"),
    path("<slug:slug>/partager/", views.group_share_result, name="share_result"),
    path("<slug:slug>/message/", views.group_send_message, name="send_message"),
    path("invitation/<int:invitation_id>/repondre/", views.respond_invitation, name="respond_invitation"),
]