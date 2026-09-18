from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import COVER_IMAGES, DEFAULT_COVER_IMAGE, Experiment


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


class CoverImageTest(TestCase):
    """Chaque expérience a sa propre couverture, sans doublon."""

    def test_mapped_slugs_use_their_unique_static_image(self):
        seen = set()
        for slug, filename in COVER_IMAGES.items():
            with self.subTest(slug=slug):
                exp = Experiment(title=slug, slug=slug, short_description="x")
                self.assertEqual(exp.cover_image, f"/static/images/{filename}")
                self.assertNotIn(filename, seen)
                seen.add(filename)

    def test_unmapped_slug_uses_generic_cover(self):
        exp = Experiment(title="Autre", slug="sans-image", short_description="x")
        self.assertEqual(exp.cover_image, f"/static/{DEFAULT_COVER_IMAGE}")

    def test_catalogue_renders_mapped_cover(self):
        Experiment.objects.create(
            title="Dosage test",
            slug="dosage-acido-basique-etalonnage-hcl",
            short_description="x",
            is_published=True,
        )
        response = self.client.get(reverse("experiments:catalogue"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/static/images/pexels-anntarazevich-8392790.jpg")
