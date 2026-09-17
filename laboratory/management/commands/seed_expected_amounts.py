"""
Seed des volumes attendus (ExpectedReagentAmount) pour chaque expérience.

Cette commande définit pour chaque réactif de chaque expérience le volume
correct à verser et la marge de tolérance acceptée. C'est la « recette » du
laboratoire : la simulation compare ensuite les volumes réellement versés par
l'utilisateur à ces valeurs pour calculer son score.

Rejouable sans risque (get_or_create partout).

UTILISATION :
    python manage.py seed_expected_amounts
"""

from django.core.management.base import BaseCommand

from experiments.models import Experiment
from laboratory.models import ExpectedReagentAmount, Reagent

# Format : titre de l'expérience -> {nom du réactif: (volume cible, tolérance)}
EXPECTED = {
    "Préparation de solutions": {
        "Hydroxyde de sodium (NaOH) solide": (4.0, 1.0),
        "Eau distillée": (80.0, 10.0),
        "Acide chlorhydrique (HCl)": (5.0, 2.0),
        "Carbonate de sodium (Na2CO3)": (5.0, 2.0),
        "Éthanol": (10.0, 3.0),
    },
    "Dosage acido-basique (étalonnage HCl)": {
        "Solution de HCl diluée": (20.0, 2.0),
        "Solution de NaOH": (12.0, 1.0),
        "Carbonate de sodium (Na2CO3)": (5.0, 2.0),
        "Bleu de bromothymol": (0.5, 0.3),
        "Méthyl-orange": (0.5, 0.3),
    },
    "Dosage d'oxydoréduction (manganimétrie)": {
        "Sulfate ferreux (FeSO4)": (10.0, 2.0),
        "Permanganate de potassium (KMnO4)": (15.0, 1.0),
        "Acide sulfurique (H2SO4)": (5.0, 1.0),
        "Eau distillée": (20.0, 5.0),
    },
    "Titrage de l'acidité totale d'un lait": {
        "Lait": (10.0, 1.0),
        "Hydroxyde de potassium (KOH)": (1.6, 0.2),
        "Phénolphtaléine": (0.5, 0.3),
        "Eau distillée": (10.0, 3.0),
    },
    "Synthèse de l'aspirine": {
        "Acide salicylique": (5.0, 1.0),
        "Anhydride acétique": (8.0, 1.5),
        "Acide sulfurique (H2SO4)": (1.0, 0.3),
        "Éthanol": (10.0, 3.0),
        "Eau distillée": (30.0, 5.0),
    },
    "Dosage de l'aspirine dans un comprimé": {
        "Comprimé d'aspirine": (1.0, 0.5),
        "Solution de NaOH": (10.0, 1.0),
        "Phénolphtaléine": (0.5, 0.3),
        "Eau distillée": (50.0, 10.0),
    },
    "Production et dosage de l'eau de Javel": {
        "Chlore (dichlore)": (5.0, 1.0),
        "Soude caustique": (10.0, 2.0),
        "Carbonate de sodium (Na2CO3)": (5.0, 2.0),
        "Iodure de potassium (KI)": (10.0, 2.0),
        "Thiosulfate de sodium": (12.0, 1.0),
        "Empois d'amidon (thiodène)": (0.5, 0.3),
        "Eau de Javel": (20.0, 3.0),
    },
    "Dosage complexométrique du calcium et du magnésium (dureté de l'eau)": {
        "EDTA (acide éthylènediaminetétracétique)": (9.0, 1.0),
        "Noir ériochrome T": (0.5, 0.3),
        "Solution tampon pH 10": (2.0, 1.0),
        "Acide calcon carboxylique": (0.5, 0.3),
        "Solution de NaOH": (5.0, 1.0),
    },
    "Extraction liquide-liquide de colorants de fruits": {
        "Hexane": (30.0, 5.0),
        "Acétate d'éthyle": (20.0, 5.0),
        "Eau distillée": (50.0, 10.0),
    },
    "Extraction des huiles essentielles": {
        "Écorces d'agrumes": (20.0, 5.0),
        "Feuilles de menthe": (20.0, 5.0),
        "Cyclohexane": (30.0, 5.0),
        "Éther diéthylique": (30.0, 5.0),
        "Eau distillée": (100.0, 20.0),
        "Chlorure de sodium (NaCl)": (5.0, 2.0),
    },
    "Synthèse du savon (saponification)": {
        "Huile alimentaire": (20.0, 3.0),
        "Huile d'olive": (20.0, 3.0),
        "Solution de NaOH": (10.0, 2.0),
        "Éthanol": (15.0, 3.0),
        "Chlorure de sodium (NaCl)": (5.0, 2.0),
        "Eau distillée": (30.0, 5.0),
    },
    "Production de savon liquide (détergent)": {
        "Texapon": (50.0, 10.0),
        "Carbonate de sodium (Na2CO3)": (5.0, 2.0),
        "Acide sulfurique (H2SO4)": (2.0, 1.0),
        "Sel de cuisine": (5.0, 2.0),
        "Colorant": (0.5, 0.3),
        "Parfum": (0.5, 0.3),
        "Eau distillée": (100.0, 20.0),
    },
    "Production d'huile végétale (coco / arachide)": {
        "Noix de coco": (20.0, 5.0),
        "Graines d'arachide": (20.0, 5.0),
        "Sel de cuisine": (5.0, 2.0),
        "Eau distillée": (50.0, 10.0),
    },
}


class Command(BaseCommand):
    help = "Définit les volumes de réactifs attendus pour chaque expérience."

    def handle(self, *args, **options):
        experiments = {e.title: e for e in Experiment.objects.all()}
        reagents = {r.name: r for r in Reagent.objects.all()}

        count = 0
        missing = []
        for title, amounts in EXPECTED.items():
            experiment = experiments.get(title)
            if experiment is None:
                missing.append(title)
                continue

            for reagent_name, (target, tolerance) in amounts.items():
                reagent = reagents.get(reagent_name)
                if reagent is None:
                    missing.append(f"{title} -> {reagent_name}")
                    continue

                _, created = ExpectedReagentAmount.objects.get_or_create(
                    experiment=experiment,
                    reagent=reagent,
                    defaults={
                        "target_volume": target,
                        "tolerance": tolerance,
                    },
                )
                count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{count} volumes attendus créés/vérifiés."
            )
        )
        if missing:
            self.stdout.write(
                self.style.WARNING("Éléments introuvables : " + ", ".join(missing))
            )