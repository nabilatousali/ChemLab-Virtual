import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Group, GroupInvitation, GroupMembership, GroupMessage


class GroupLeaderTest(TestCase):
    """Seul le chef peut inviter, retirer, transférer et supprimer."""

    def setUp(self):
        self.chef = User.objects.create_user(username="chef", password="testpass123")
        self.member = User.objects.create_user(username="membre", password="testpass123")
        self.group = Group.objects.create(
            name="Groupe", description="", created_by=self.chef, leader=self.chef
        )
        GroupMembership.objects.create(group=self.group, user=self.chef)
        GroupMembership.objects.create(group=self.group, user=self.member)

    def test_creator_becomes_leader(self):
        self.client.force_login(self.chef)
        self.client.post(reverse("groups:create"), {"name": "Nouveau", "description": ""})
        group = Group.objects.get(name="Nouveau")
        self.assertEqual(group.leader, self.chef)

    def test_member_cannot_invite(self):
        outsider = User.objects.create_user(username="externe", email="externe@example.com")
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("groups:invite_member", args=[self.group.slug]),
            {"email": "externe@example.com"},
        )
        self.assertRedirects(
            response, reverse("groups:detail", args=[self.group.slug])
        )
        self.assertFalse(
            GroupInvitation.objects.filter(
                group=self.group, invited_user=outsider
            ).exists()
        )

    def test_leader_can_invite(self):
        outsider = User.objects.create_user(username="externe", email="externe@example.com")
        self.client.force_login(self.chef)
        self.client.post(
            reverse("groups:invite_member", args=[self.group.slug]),
            {"email": "EXTERNE@EXAMPLE.COM"},
        )
        self.assertTrue(
            GroupInvitation.objects.filter(
                group=self.group, invited_user=outsider, status="pending"
            ).exists()
        )

    def test_leader_can_remove_member(self):
        self.client.force_login(self.chef)
        response = self.client.post(
            reverse("groups:remove_member", args=[self.group.slug, self.member.id])
        )
        self.assertRedirects(
            response, reverse("groups:detail", args=[self.group.slug])
        )
        self.assertFalse(
            GroupMembership.objects.filter(
                group=self.group, user=self.member
            ).exists()
        )

    def test_member_cannot_remove_anyone(self):
        self.client.force_login(self.member)
        self.client.post(
            reverse("groups:remove_member", args=[self.group.slug, self.chef.id])
        )
        self.assertTrue(
            GroupMembership.objects.filter(group=self.group, user=self.chef).exists()
        )

    def test_leader_cannot_remove_self(self):
        self.client.force_login(self.chef)
        self.client.post(
            reverse("groups:remove_member", args=[self.group.slug, self.chef.id])
        )
        self.assertTrue(
            GroupMembership.objects.filter(group=self.group, user=self.chef).exists()
        )

    def test_transfer_direction(self):
        self.client.force_login(self.chef)
        self.client.post(
            reverse("groups:transfer", args=[self.group.slug]),
            {"username": "membre"},
        )
        self.group.refresh_from_db()
        self.assertEqual(self.group.leader, self.member)

    def test_member_cannot_transfer(self):
        self.client.force_login(self.member)
        self.client.post(
            reverse("groups:transfer", args=[self.group.slug]),
            {"username": "membre"},
        )
        self.group.refresh_from_db()
        self.assertEqual(self.group.leader, self.chef)

    def test_member_can_leave(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("groups:leave", args=[self.group.slug]))
        self.assertRedirects(response, reverse("groups:list"))
        self.assertFalse(
            GroupMembership.objects.filter(
                group=self.group, user=self.member
            ).exists()
        )

    def test_leader_leaving_transfers_to_oldest_member(self):
        senior = User.objects.create_user(username="ancien")
        GroupMembership.objects.create(group=self.group, user=senior)
        self.client.force_login(self.chef)
        self.client.post(reverse("groups:leave", args=[self.group.slug]))
        self.group.refresh_from_db()
        # "membre" (créé dans setUp) est plus ancien que "ancien".
        self.assertEqual(self.group.leader, self.member)
        self.assertTrue(Group.objects.filter(pk=self.group.pk).exists())

    def test_last_member_leaving_deletes_group(self):
        GroupMembership.objects.filter(group=self.group, user=self.member).delete()
        self.client.force_login(self.chef)
        self.client.post(reverse("groups:leave", args=[self.group.slug]))
        self.assertFalse(Group.objects.filter(pk=self.group.pk).exists())

    def test_leader_can_delete_group(self):
        self.client.force_login(self.chef)
        response = self.client.post(
            reverse("groups:delete", args=[self.group.slug])
        )
        self.assertRedirects(response, reverse("groups:list"))
        self.assertFalse(Group.objects.filter(pk=self.group.pk).exists())

    def test_member_cannot_delete_group(self):
        self.client.force_login(self.member)
        self.client.post(reverse("groups:delete", args=[self.group.slug]))
        self.assertTrue(Group.objects.filter(pk=self.group.pk).exists())


class GroupChatRealtimeTest(TestCase):
    """Chat temps réel : envoi AJAX + polling des nouveaux messages."""

    def setUp(self):
        self.chef = User.objects.create_user(username="chef", password="testpass123")
        self.member = User.objects.create_user(username="membre", password="testpass123")
        self.outsider = User.objects.create_user(
            username="externe", password="testpass123"
        )
        self.group = Group.objects.create(
            name="Groupe", description="", created_by=self.chef, leader=self.chef
        )
        GroupMembership.objects.create(group=self.group, user=self.chef)
        GroupMembership.objects.create(group=self.group, user=self.member)
        self.first = GroupMessage.objects.create(
            group=self.group, sender=self.chef, content="Bonjour"
        )

    def ajax_post_message(self, user, content):
        self.client.force_login(user)
        return self.client.post(
            reverse("groups:send_message", args=[self.group.slug]),
            {"content": content},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_ajax_send_returns_json_without_reload(self):
        response = self.ajax_post_message(self.member, "Salut !")
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["message"]["content"], "Salut !")
        self.assertEqual(payload["message"]["sender"], "membre")
        self.assertTrue(payload["message"]["mine"])

    def test_classic_post_still_redirects(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("groups:send_message", args=[self.group.slug]),
            {"content": "Classique"},
        )
        self.assertRedirects(
            response, reverse("groups:detail", args=[self.group.slug])
        )

    def test_empty_message_is_ignored(self):
        response = self.ajax_post_message(self.member, "   ")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(json.loads(response.content)["message"])
        self.assertEqual(GroupMessage.objects.filter(group=self.group).count(), 1)

    def test_polling_returns_only_new_messages(self):
        self.client.force_login(self.member)
        response = self.client.get(
            reverse("groups:messages_json", args=[self.group.slug]),
            {"after": self.first.id},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["messages"], [])

        GroupMessage.objects.create(
            group=self.group, sender=self.chef, content="Nouveau"
        )
        response = self.client.get(
            reverse("groups:messages_json", args=[self.group.slug]),
            {"after": self.first.id},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        messages = json.loads(response.content)["messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["content"], "Nouveau")
        self.assertFalse(messages[0]["mine"])

    def test_non_member_cannot_read_or_write(self):
        self.client.force_login(self.outsider)
        response = self.client.get(
            reverse("groups:messages_json", args=[self.group.slug])
        )
        self.assertEqual(response.status_code, 403)
        response = self.ajax_post_message(self.outsider, "Intrus")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(GroupMessage.objects.filter(group=self.group).count(), 1)
