from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Experiment


class CatalogueViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        Experiment.objects.create(
            title="Test Experiment",
            slug="test-experiment",
            short_description="A test experiment",
            is_published=True,
        )

    def test_catalogue_renders(self):
        response = self.client.get(reverse("experiments:catalogue"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Experiment")


class DetailViewTest(TestCase):

    def setUp(self):
        Experiment.objects.create(
            title="Test Experiment",
            slug="test-experiment",
            short_description="A test experiment",
            is_published=True,
        )

    def test_detail_renders(self):
        response = self.client.get(
            reverse("experiments:detail", args=["test-experiment"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Experiment")

    def test_detail_404_unpublished(self):
        Experiment.objects.create(
            title="Hidden",
            slug="hidden",
            short_description="Nope",
            is_published=False,
        )
        response = self.client.get(
            reverse("experiments:detail", args=["hidden"])
        )
        self.assertEqual(response.status_code, 404)


class ExperimentModelTest(TestCase):

    def test_str(self):
        exp = Experiment(title="Mon Test", slug="mon-test", short_description="x")
        self.assertEqual(str(exp), "Mon Test")

    def test_get_absolute_url(self):
        exp = Experiment(title="T", slug="t", short_description="x")
        self.assertEqual(exp.get_absolute_url(), reverse("experiments:detail", args=["t"]))
