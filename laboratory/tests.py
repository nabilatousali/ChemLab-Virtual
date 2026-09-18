from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

import json
from unittest import mock

import requests

from experiments.models import Experiment
from .models import (
    ExpectedReagentAmount,
    ExperimentResult,
    Material,
    Reagent,
    UserBenchReagent,
)
from .services import pubchem


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

    def test_dashboard_renders_experiment_covers(self):
        Experiment.objects.create(
            title="Préparation",
            slug="preparation-de-solutions",
            short_description="Test",
            is_published=True,
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("laboratory:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "/static/images/pexels-mikhail-nilov-8850993.jpg"
        )


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


# =====================================================================
# Service PubChem (mock complet de l'API, jamais de réseau en test)
# =====================================================================

class PubChemServiceTest(TestCase):

    def setUp(self):
        cache.clear()

    @staticmethod
    def _fake_response(status_code, payload):
        response = mock.Mock()
        response.status_code = status_code
        response.json.return_value = payload
        return response

    def test_search_serializes_candidates(self):
        cids = {"IdentifierList": {"CID": [2244, 3032689]}}
        props = {
            "PropertyTable": {
                "Properties": [
                    {
                        "CID": 2244,
                        "IUPACName": "Aspirin",
                        "MolecularFormula": "C9H8O4",
                        "MolecularWeight": 180.16,
                    },
                    {
                        "CID": 3032689,
                        "IUPACName": "Autre composé",
                        "MolecularFormula": "",
                        "MolecularWeight": None,
                    },
                ]
            }
        }
        with mock.patch("laboratory.services.pubchem.requests.get") as mocked_get:
            mocked_get.side_effect = [
                self._fake_response(200, cids),
                self._fake_response(200, props),
            ]
            results = pubchem.search_compounds("aspirin")

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["cid"], 2244)
        self.assertEqual(results[0]["name"], "Aspirin")
        self.assertEqual(results[0]["formula"], "C9H8O4")
        self.assertTrue(results[0]["image_url"].endswith("/PNG"))

    def test_search_not_found_raises(self):
        with mock.patch(
            "laboratory.services.pubchem.requests.get",
            return_value=self._fake_response(404, {}),
        ):
            with self.assertRaises(pubchem.PubChemNotFound):
                pubchem.search_compounds("xyzzy-inconnu")

    def test_search_timeout_raises_pubchem_error(self):
        with mock.patch(
            "laboratory.services.pubchem.requests.get",
            side_effect=requests.Timeout,
        ):
            with self.assertRaises(pubchem.PubChemError):
                pubchem.search_compounds("aspirin")

    def test_search_rate_limited_raises(self):
        with mock.patch(
            "laboratory.services.pubchem.requests.get",
            return_value=self._fake_response(429, {}),
        ):
            with self.assertRaises(pubchem.PubChemRateLimited):
                pubchem.search_compounds("aspirin")

    def test_search_invalid_json_raises_pubchem_error(self):
        response = mock.Mock()
        response.status_code = 200
        response.json.side_effect = ValueError()
        with mock.patch(
            "laboratory.services.pubchem.requests.get", return_value=response
        ):
            with self.assertRaises(pubchem.PubChemError):
                pubchem.search_compounds("aspirin")

    def test_search_empty_result_list(self):
        with mock.patch(
            "laboratory.services.pubchem.requests.get",
            return_value=self._fake_response(200, {"IdentifierList": {"CID": []}}),
        ):
            self.assertEqual(pubchem.search_compounds("rien"), [])

    def test_get_details_gathers_synonyms(self):
        props = {
            "PropertyTable": {
                "Properties": [
                    {
                        "CID": 2244,
                        "IUPACName": "Aspirin",
                        "MolecularFormula": "C9H8O4",
                        "MolecularWeight": 180.16,
                        "CanonicalSMILES": "CC(=O)Oc1ccccc1C(=O)O",
                        "IsomericSMILES": "",
                        "InChI": "InChI=1S/C9H8O4/c...",
                        "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
                    }
                ]
            }
        }
        synonyms = {
            "InformationList": {
                "Information": [{"CID": 2244, "Synonym": ["Aspirin", "Aspirine"]}]
            }
        }
        with mock.patch("laboratory.services.pubchem.requests.get") as mocked_get:
            mocked_get.side_effect = [
                self._fake_response(200, props),
                self._fake_response(200, synonyms),
            ]
            details = pubchem.get_compound_details(2244)

        self.assertEqual(details["name"], "Aspirin")
        self.assertEqual(details["inchikey"], "BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        self.assertEqual(details["synonyms"], ["Aspirin", "Aspirine"])


# =====================================================================
# Paillasse libre (vues)
# =====================================================================

class PubChemBenchViewTest(TestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="bench", password="testpass123")

    def test_bench_requires_login(self):
        response = self.client.get(reverse("laboratory:bench"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_search_renders_candidates(self):
        self.client.force_login(self.user)
        candidates = [
            {
                "cid": 2244,
                "name": "Aspirin",
                "formula": "C9H8O4",
                "weight": 180.16,
                "image_url": "https://img.test/2244.png",
            }
        ]
        with mock.patch.object(
            pubchem, "search_compounds", return_value=candidates
        ):
            response = self.client.get(reverse("laboratory:bench"), {"q": "aspirin"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aspirin")

    def test_search_not_found_displays_message(self):
        self.client.force_login(self.user)
        with mock.patch.object(
            pubchem, "search_compounds", side_effect=pubchem.PubChemNotFound
        ):
            response = self.client.get(reverse("laboratory:bench"), {"q": "xyzzy"})
        self.assertContains(response, "Aucun composé trouvé")

    def test_search_rate_limited_displays_message(self):
        self.client.force_login(self.user)
        with mock.patch.object(
            pubchem, "search_compounds", side_effect=pubchem.PubChemRateLimited
        ):
            response = self.client.get(reverse("laboratory:bench"), {"q": "aspirin"})
        self.assertContains(response, "trop de requêtes")

    def test_search_unavailable_displays_message(self):
        self.client.force_login(self.user)
        with mock.patch.object(
            pubchem, "search_compounds", side_effect=pubchem.PubChemError("hors ligne")
        ):
            response = self.client.get(reverse("laboratory:bench"), {"q": "aspirin"})
        self.assertContains(response, "momentanément indisponible")

    def test_add_reagent_creates_bench_entry(self):
        self.client.force_login(self.user)
        details = {
            "cid": 2244,
            "name": "Aspirin",
            "formula": "C9H8O4",
            "weight": 180.16,
            "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
            "isomeric_smiles": "",
            "inchi": "InChI=1S/C9H8O4",
            "inchikey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "synonyms": ["Aspirin", "Aspirine"],
            "image_url": "https://img.test/2244.png",
        }
        with mock.patch.object(
            pubchem, "get_compound_details", return_value=details
        ), mock.patch.object(
            pubchem,
            "get_ghs_data",
            return_value={"pictograms": ["GHS07"], "statements": []},
        ):
            response = self.client.post(
                reverse("laboratory:bench_add", args=[2244])
            )
        self.assertRedirects(response, reverse("laboratory:bench"))

        reagent = UserBenchReagent.objects.get(user=self.user, pubchem_cid=2244)
        self.assertEqual(reagent.name, "Aspirin")
        self.assertEqual(reagent.hazards, "GHS07")
        self.assertEqual(reagent.molecular_formula, "C9H8O4")
        self.assertEqual(reagent.molecular_weight, 180.16)
        self.assertEqual(
            reagent.inchikey, "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        )

    def test_add_duplicate_is_rejected(self):
        self.client.force_login(self.user)
        UserBenchReagent.objects.create(
            user=self.user, name="Aspirin", pubchem_cid=2244
        )
        with mock.patch.object(pubchem, "get_compound_details"):
            response = self.client.post(
                reverse("laboratory:bench_add", args=[2244])
            )
        self.assertRedirects(response, reverse("laboratory:bench"))
        self.assertEqual(UserBenchReagent.objects.filter(user=self.user).count(), 1)

    def test_add_not_found_creates_nothing(self):
        self.client.force_login(self.user)
        with mock.patch.object(
            pubchem, "get_compound_details", side_effect=pubchem.PubChemNotFound
        ):
            response = self.client.post(
                reverse("laboratory:bench_add", args=[9999999])
            )
        self.assertRedirects(response, reverse("laboratory:bench"))
        self.assertEqual(UserBenchReagent.objects.count(), 0)

    def test_remove_deletes_own_reagent(self):
        self.client.force_login(self.user)
        reagent = UserBenchReagent.objects.create(
            user=self.user, name="Aspirin", pubchem_cid=2244
        )
        response = self.client.post(
            reverse("laboratory:bench_remove", args=[reagent.pk])
        )
        self.assertRedirects(response, reverse("laboratory:bench"))
        self.assertFalse(UserBenchReagent.objects.filter(pk=reagent.pk).exists())

    def test_cannot_remove_other_users_reagent(self):
        other = User.objects.create_user(username="autre", password="testpass123")
        reagent = UserBenchReagent.objects.create(
            user=other, name="Aspirin", pubchem_cid=2244
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("laboratory:bench_remove", args=[reagent.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(UserBenchReagent.objects.filter(pk=reagent.pk).exists())

    def test_simulate_computes_derived_quantities(self):
        self.client.force_login(self.user)
        r1 = UserBenchReagent.objects.create(
            user=self.user,
            name="Acide chlorhydrique",
            pubchem_cid=313,
            molecular_formula="HCl",
            molecular_weight=36.46,
            color="#2563eb",
        )
        r2 = UserBenchReagent.objects.create(
            user=self.user,
            name="Soude",
            pubchem_cid=14798,
            molecular_formula="NaOH",
            molecular_weight=39.997,
            color="#0d9488",
        )

        response = self.client.post(
            reverse("laboratory:bench_simulate"),
            {
                f"volume_{r1.pk}": "10",
                f"conc_{r1.pk}": "1",
                f"volume_{r2.pk}": "5",
                f"conc_{r2.pk}": "0.5",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Résultats de la simulation")

        r1.refresh_from_db()
        r2.refresh_from_db()
        self.assertEqual(r1.volume_ml, 10.0)
        self.assertEqual(r1.concentration, 1.0)

        # n(HCl) = 1 × 10/1000 = 0.01 mol ; n(NaOH) = 0.5 × 5/1000 = 0.0025 mol
        self.assertContains(response, "15.0 mL")
        self.assertContains(response, "0.0125")

        # m totale = 0.01 × 36.46 + 0.0025 × 39.997 = 0.4646 g
        self.assertContains(response, "0.46 g")

    def test_simulate_without_concentration_skips_amount(self):
        self.client.force_login(self.user)
        reagent = UserBenchReagent.objects.create(
            user=self.user,
            name="Eau",
            pubchem_cid=962,
            molecular_formula="H2O",
            molecular_weight=18.015,
        )
        response = self.client.post(
            reverse("laboratory:bench_simulate"),
            {f"volume_{reagent.pk}": "25", f"conc_{reagent.pk}": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "indiquez une concentration")
        reagent.refresh_from_db()
        self.assertEqual(reagent.volume_ml, 25.0)
        self.assertIsNone(reagent.concentration)

    def test_reagents_are_not_shared_between_users(self):
        self.client.force_login(self.user)
        second = User.objects.create_user(username="second", password="testpass123")
        UserBenchReagent.objects.create(
            user=second, name="Thiosulfate de sodium", pubchem_cid=516951
        )
        response = self.client.get(reverse("laboratory:bench"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Thiosulfate")


class FreeLaboratoryTest(TestCase):
    """Le laboratoire libre : catalogue complet, sans protocole, analyse du mélange."""

    def setUp(self):
        self.user = User.objects.create_user(username="libre", password="testpass123")
        self.material = Material.objects.create(name="Bécher")
        self.acid = Reagent.objects.create(name="Acide test", color="#ff0000", ph=1.0)
        self.base = Reagent.objects.create(name="Base test", color="#0000ff", ph=13.0)
        self.water = Reagent.objects.create(name="Eau test")
        self.analyze_url = reverse("laboratory:analyze_mixture")

    def post_mixture(self, pours):
        return self.client.post(
            self.analyze_url,
            json.dumps({"containers": [{"material": "Bécher", "pours": pours}]}),
            content_type="application/json",
        )

    def test_free_lab_requires_login(self):
        lab_url = reverse("laboratory:laboratory")
        response = self.client.get(lab_url)
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={lab_url}"
        )

    def test_free_lab_renders_full_catalog_without_protocol(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("laboratory:laboratory"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Laboratoire libre")
        self.assertContains(response, "Acide test")
        self.assertContains(response, "Bécher")
        self.assertContains(response, "Analyser le mélange")
        self.assertNotContains(response, "Protocole")

    def test_analyze_returns_volume_color_ph_and_composition(self):
        self.client.force_login(self.user)
        response = self.post_mixture([
            {"reagent": "Acide test", "volume": 10},
            {"reagent": "Base test", "volume": 10},
        ])
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_volume"], 20.0)
        self.assertEqual(data["mixed_color"], "#800080")
        self.assertAlmostEqual(data["ph"], 1.3)
        self.assertEqual(data["indicators"]["volume"]["value"], 20.0)
        self.assertEqual(data["indicators"]["color"]["value"], "#800080")
        self.assertEqual(data["indicators"]["count"]["value"], 2)
        self.assertEqual(len(data["composition"]), 2)
        self.assertEqual(data["composition"][0]["percent"], 50.0)

    def test_analyze_colorless_reagent_dilutes_color(self):
        self.client.force_login(self.user)
        response = self.post_mixture([
            {"reagent": "Acide test", "volume": 10},
            {"reagent": "Eau test", "volume": 10},
        ])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mixed_color"], "#fa7d7e")

    def test_analyze_without_ph_counts_reagent_as_neutral(self):
        self.client.force_login(self.user)
        response = self.post_mixture([{"reagent": "Eau test", "volume": 20}])
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["ph"], 7.0)
        self.assertTrue(any("neutre" in w for w in data["warnings"]))

    def test_analyze_empty_mixture_returns_400(self):
        self.client.force_login(self.user)
        response = self.post_mixture([])
        self.assertEqual(response.status_code, 400)

    def test_analyze_invalid_payload_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.analyze_url, "ceci n'est pas du json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_free_lab_lists_user_bench_reagents(self):
        UserBenchReagent.objects.create(
            user=self.user, name="Composé perso", pubchem_cid=123, color="#00ff00"
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("laboratory:laboratory"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ma paillasse")
        self.assertContains(response, "Composé perso")

    def test_free_lab_does_not_list_other_users_bench(self):
        other = User.objects.create_user(username="autre", password="testpass123")
        UserBenchReagent.objects.create(
            user=other, name="Composé secret", pubchem_cid=999
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("laboratory:laboratory"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Composé secret")

    def test_analyze_uses_bench_reagent_color_and_neutral_ph(self):
        UserBenchReagent.objects.create(
            user=self.user, name="Composé perso", pubchem_cid=123, color="#00ff00"
        )
        self.client.force_login(self.user)
        response = self.post_mixture([{"reagent": "Composé perso", "volume": 10}])
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mixed_color"], "#00ff00")
        self.assertEqual(data["ph"], 7.0)
        self.assertTrue(any("paillasse" in w for w in data["warnings"]))


class SafetyAlertsTest(TestCase):
    """Alertes de sécurité : pictogrammes SGH, conseils, incompatibilités."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="secu", password="testpass123")
        self.javel = Reagent.objects.create(
            name="Eau de Javel",
            color="#ffffff",
            hazards="GHS05,GHS09",
            safety_advice="Ne jamais mélanger avec un acide.",
        )
        self.acid = Reagent.objects.create(
            name="Acide test", color="#ff0000", hazards="GHS05"
        )
        self.javel.incompatible_with.add(self.acid)

    def test_hazard_list_parsing(self):
        self.assertEqual(self.javel.hazard_list, ["GHS05", "GHS09"])
        self.assertTrue(self.javel.has_danger)
        neutral = Reagent.objects.create(name="Eau")
        self.assertEqual(neutral.hazard_list, [])
        self.assertFalse(neutral.has_danger)

    def test_unknown_hazard_code_rejected(self):
        reagent = Reagent(name="Douteux", hazards="GHS99")
        with self.assertRaises(ValidationError):
            reagent.full_clean()

    def test_incompatibility_is_symmetrical(self):
        self.assertIn(self.javel, list(self.acid.incompatible_with.all()))

    def test_admin_form_saves_hazard_checks(self):
        from .admin import ReagentAdminForm

        form = ReagentAdminForm(
            data={"name": "Solvant", "hazard_checks": ["GHS02", "GHS07"]},
            instance=Reagent(name="Solvant"),
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().hazards, "GHS02,GHS07")

    def test_ghs_parsing_from_pubchem_payload(self):
        payload = {
            "Record": {
                "Section": [
                    {
                        "TOCHeading": "Safety and Hazards",
                        "Section": [
                            {
                                "TOCHeading": "Hazards Identification",
                                "Section": [
                                    {
                                        "TOCHeading": "GHS Classification",
                                        "Information": [
                                            {
                                                "Name": "Pictogram(s)",
                                                "Value": {
                                                    "StringWithMarkup": [
                                                        {
                                                            "String": "  ",
                                                            "Markup": [
                                                                {
                                                                    "URL": "https://pubchem.ncbi.nlm.nih.gov/images/ghs/GHS05.svg",
                                                                    "Type": "Icon",
                                                                    "Extra": "Corrosive",
                                                                },
                                                                {
                                                                    "URL": "https://pubchem.ncbi.nlm.nih.gov/images/ghs/GHS07.svg",
                                                                    "Type": "Icon",
                                                                    "Extra": "Irritant",
                                                                },
                                                            ],
                                                        }
                                                    ]
                                                },
                                            },
                                            {
                                                "Name": "GHS Hazard Statements",
                                                "Value": {
                                                    "StringWithMarkup": [
                                                        {
                                                            "String": "H314: Causes severe skin burns and eye damage"
                                                        }
                                                    ]
                                                },
                                            },
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }
        response = mock.Mock(status_code=200)
        response.json.return_value = payload
        with mock.patch(
            "laboratory.services.pubchem.requests.get", return_value=response
        ):
            data = pubchem.get_ghs_data(999001)
        self.assertEqual(data["pictograms"], ["GHS05", "GHS07"])
        self.assertEqual(
            data["statements"], ["H314: Causes severe skin burns and eye damage"]
        )

    def test_bench_add_stores_ghs(self):
        self.client.force_login(self.user)
        details = {
            "cid": 999002,
            "name": "Composé test",
            "formula": "H2O",
            "weight": 18.015,
            "canonical_smiles": "",
            "isomeric_smiles": "",
            "inchi": "",
            "inchikey": "",
            "synonyms": [],
            "image_url": "",
        }
        with mock.patch.object(
            pubchem, "get_compound_details", return_value=details
        ), mock.patch.object(
            pubchem,
            "get_ghs_data",
            return_value={"pictograms": ["GHS05"], "statements": ["H314: danger"]},
        ):
            self.client.post(reverse("laboratory:bench_add", args=[999002]))
        reagent = UserBenchReagent.objects.get(user=self.user, pubchem_cid=999002)
        self.assertEqual(reagent.hazards, "GHS05")
        self.assertIn("H314", reagent.hazard_statements)

    def test_analyze_reports_safety(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("laboratory:analyze_mixture"),
            json.dumps(
                {
                    "containers": [
                        {
                            "material": "Bécher",
                            "pours": [
                                {"reagent": "Eau de Javel", "volume": 10},
                                {"reagent": "Acide test", "volume": 10},
                            ],
                        }
                    ]
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        safety = response.json()["safety"]
        self.assertTrue(safety["has_danger"])
        self.assertEqual(
            [pic["code"] for pic in safety["pictograms"]], ["GHS05", "GHS09"]
        )
        self.assertTrue(any("incompatible" in w for w in safety["warnings"]))
        self.assertTrue(
            any(item["reagent"] == "Eau de Javel" for item in safety["advice"])
        )

    def test_free_lab_page_exposes_safety_data(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("laboratory:laboratory"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-hazards="GHS05,GHS09"')
        self.assertContains(response, "safetyModalOverlay")
        self.assertContains(response, "ghs-labels")
        self.assertContains(response, "Corrosif")