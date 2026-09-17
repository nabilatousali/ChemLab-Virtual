from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from experiments.models import Experiment
from .models import (
    ExpectedReagentAmount,
    ExperimentResult,
    Material,
    Reagent,
)


class WorkspaceViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="labo", password="testpass123")
        self.experiment = Experiment.objects.create(
            title="Dosage test",
            slug="dosage-test",
            short_description="Test",
            is_published=True,
        )

        self.material = Material.objects.create(name="Erlenmeyer")
        self.reagent_hcl = Reagent.objects.create(name="Acide chlorhydrique")
        self.reagent_naoh = Reagent.objects.create(name="Soude")

        ExpectedReagentAmount.objects.create(
            experiment=self.experiment,
            reagent=self.reagent_hcl,
            target_volume=10.0,
            tolerance=1.0,
        )
        ExpectedReagentAmount.objects.create(
            experiment=self.experiment,
            reagent=self.reagent_naoh,
            target_volume=8.0,
            tolerance=2.0,
        )

    def test_workspace_requires_login(self):
        response = self.client.get(
            reverse("laboratory:workspace", args=[self.experiment.slug])
        )
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('laboratory:workspace', args=[self.experiment.slug])}",
        )

    def test_workspace_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("laboratory:workspace", args=[self.experiment.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dosage test")


class SubmitExperimentTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="labo", password="testpass123")
        self.experiment = Experiment.objects.create(
            title="Dosage test",
            slug="dosage-test",
            short_description="Test",
            is_published=True,
        )

        self.material = Material.objects.create(name="Erlenmeyer")
        self.reagent_hcl = Reagent.objects.create(
            name="Acide chlorhydrique", color="#ff0000"
        )
        self.reagent_naoh = Reagent.objects.create(
            name="Soude", color="#00ff00"
        )

        ExpectedReagentAmount.objects.create(
            experiment=self.experiment,
            reagent=self.reagent_hcl,
            target_volume=10.0,
            tolerance=1.0,
        )
        ExpectedReagentAmount.objects.create(
            experiment=self.experiment,
            reagent=self.reagent_naoh,
            target_volume=8.0,
            tolerance=2.0,
        )

        self.url = reverse("laboratory:submit_result", args=[self.experiment.slug])

    def test_submit_requires_login(self):
        response = self.client.post(self.url, data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 302)

    def _post(self, pours):
        return self.client.post(
            self.url,
            data={
                "containers": [
                    {"material": "Erlenmeyer", "pours": pours},
                ]
            },
            content_type="application/json",
        )

    def test_correct_volumes_succeed(self):
        self.client.force_login(self.user)
        response = self._post(
            [
                {"reagent": "Acide chlorhydrique", "volume": 10},
                {"reagent": "Soude", "volume": 8},
            ]
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["is_successful"])
        self.assertGreaterEqual(payload["score"], 80)

    def test_wrong_volumes_fail(self):
        self.client.force_login(self.user)
        response = self._post(
            [
                {"reagent": "Acide chlorhydrique", "volume": 50},
                {"reagent": "Soude", "volume": 50},
            ]
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["is_successful"])
        self.assertLess(payload["score"], 80)

    def test_result_is_saved(self):
        self.client.force_login(self.user)
        self._post(
            [
                {"reagent": "Acide chlorhydrique", "volume": 10},
                {"reagent": "Soude", "volume": 8},
            ]
        )
        self.assertEqual(ExperimentResult.objects.count(), 1)
        saved = ExperimentResult.objects.first()
        self.assertEqual(saved.user, self.user)
        self.assertEqual(saved.experiment, self.experiment)
        self.assertTrue(saved.is_successful)