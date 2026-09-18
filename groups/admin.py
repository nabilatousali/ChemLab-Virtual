from django.contrib import admin

from .models import Group, GroupMembership, GroupInvitation, SharedResult, GroupMessage


class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 0


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "leader", "created_at")
    search_fields = ("name", "description")
    search_fields = ("name", "description")
    date_hierarchy = "created_at"
    inlines = [GroupMembershipInline]


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ("group", "user", "joined_at")
    list_filter = ("group",)
    search_fields = ("group__name", "user__username")


@admin.register(GroupInvitation)
class GroupInvitationAdmin(admin.ModelAdmin):
    list_display = ("group", "invited_user", "invited_by", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("group__name", "invited_user__username")
    date_hierarchy = "created_at"


@admin.register(SharedResult)
class SharedResultAdmin(admin.ModelAdmin):
    list_display = ("group", "result", "shared_by", "shared_at")
    list_filter = ("group",)
    search_fields = ("group__name", "shared_by__username")


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ("group", "sender", "sent_at")
    list_filter = ("group",)
    search_fields = ("group__name", "sender__username", "content")
    date_hierarchy = "sent_at"
