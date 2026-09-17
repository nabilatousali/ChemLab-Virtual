from django.contrib import admin

from .models import Group, GroupMembership, GroupInvitation, SharedResult, GroupMessage


class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 1


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at")
    inlines = [GroupMembershipInline]


@admin.register(GroupInvitation)
class GroupInvitationAdmin(admin.ModelAdmin):
    list_display = ("group", "invited_user", "invited_by", "status", "created_at")
    list_filter = ("status",)


admin.site.register(GroupMembership)
admin.site.register(SharedResult)
admin.site.register(GroupMessage) 