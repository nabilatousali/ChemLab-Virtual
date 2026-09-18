"""
Commande d'import des données extraites des manuels de TP de Chimie
(Niveau 1, Niveau 2, Niveau 3).

INSTALLATION :
    Place ce fichier ici dans ton projet :
    laboratory/management/commands/import_tp_data.py

    (crée les dossiers manquants : laboratory/management/
     et laboratory/management/commands/, avec un fichier vide
     __init__.py dans chacun des deux, sinon Django ne détectera
     pas la commande)

UTILISATION :
    python manage.py import_tp_data

Le script est rejouable sans risque (get_or_create partout) :
si tu le relances, il ne crée pas de doublons.
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from experiments.models import Experiment
from laboratory.models import (
    Material,
    Reagent,
    ExperimentMaterial,
    ExperimentReagent,
    ProtocolStep,
    Indicator,
    ReactionType,
    ExperimentConfig,
    ExperimentIndicator,
)


class Command(BaseCommand):
    help = "Importe les matériels, réactifs, catégories et expériences des manuels de TP"

    def handle(self, *args, **options):
        materials = self.create_materials()
        reagents = self.create_reagents()
        indicators = self.create_indicators()
        reaction_types = self.create_reaction_types(indicators)
        self.create_experiments(materials, reagents, indicators, reaction_types)
        self.stdout.write(self.style.SUCCESS("Import terminé avec succès."))

    # ------------------------------------------------------------------
    # MATERIEL
    # ------------------------------------------------------------------
    def create_materials(self):
        names = [
            "Bécher",
            "Erlenmeyer",
            "Fiole conique",
            "Ballon mono col rodé",
            "Ballon mono col",
            "Ballon bi-col",
            "Ballon tri-col",
            "Éprouvette graduée",
            "Burette",
            "Fiole jaugée",
            "Pipette graduée",
            "Pipette jaugée",
            "Propipette",
            "Entonnoir",
            "Réfrigérant",
            "Trépied",
            "Mortier",
            "Bec Bünsen",
            "Plaque chauffante avec agitation",
            "Chauffe-ballon",
            "Ampoule à décanter",
            "Pissette",
            "Verre de montre",
            "Spatule",
            "Tube à essais",
            "pH-mètre",
            "Balance analytique",
            "Agitateur magnétique",
            "Barreau aimanté",
            "Statif",
            "Pince",
            "Thermomètre",
            "Évaporateur (Rotavapeur)",
            "Büchner",
            "Étuve",
            "Bain-marie",
            "Tamis",
            "Presse / mixeur",
            "Seaux et agitateurs",
            "Casserole",
        ]
        result = {}
        for name in names:
            obj, _ = Material.objects.get_or_create(name=name)
            result[name] = obj
        self.stdout.write(f"{len(result)} matériels créés/vérifiés.")
        return result

    # ------------------------------------------------------------------
    # REACTIFS
    # ------------------------------------------------------------------
    def create_reagents(self):
        # (nom, couleur, concentration)
        data = [
            ("Hydroxyde de sodium (NaOH) solide", "", ""),
            ("Solution de NaOH", "#e8f4f8", "0,1 N"),
            ("Acide chlorhydrique (HCl)", "", "37% commercial"),
            ("Solution de HCl diluée", "", "0,1 N"),
            ("Permanganate de potassium (KMnO4)", "#8e44ad", "0,1 M"),
            ("Acide sulfurique (H2SO4)", "", "concentré"),
            ("Sulfate ferreux (FeSO4)", "#b7c9a8", ""),
            ("Hydroxyde de potassium (KOH)", "", "0,025 M"),
            ("Lait", "#fdfdfd", ""),
            ("Phénolphtaléine", "", "indicateur coloré"),
            ("Bleu de bromothymol", "#3498db", "indicateur coloré"),
            ("Hélianthine", "#e67e22", "indicateur coloré"),
            ("Jaune d'alizarine", "#f1c40f", "indicateur coloré"),
            ("Rouge de méthyle", "#e74c3c", "indicateur coloré"),
            ("Méthyl-orange", "#e67e22", "indicateur coloré"),
            ("Acide salicylique", "", "solide blanc"),
            ("Anhydride acétique", "", ""),
            ("Éthanol", "", "90°"),
            ("Eau distillée", "", ""),
            ("Comprimé d'aspirine", "", "500 mg"),
            ("Iodure de potassium (KI)", "", "100 g/L"),
            ("Thiosulfate de sodium", "", "0,1 mol/L"),
            ("Empois d'amidon (thiodène)", "", "indicateur"),
            ("Eau de Javel", "", "commerciale"),
            ("Carbonate de sodium (Na2CO3)", "", ""),
            ("Cyclohexane", "", "solvant"),
            ("Éther diéthylique", "", "solvant"),
            ("Chlorure de sodium (NaCl)", "", ""),
            ("Huile alimentaire", "#f4d35e", ""),
            ("Texapon", "", ""),
            ("Colorant", "", ""),
            ("Parfum", "", ""),
            ("Chlore (dichlore)", "", ""),
            ("Soude caustique", "", ""),
            ("EDTA (acide éthylènediaminetétracétique)", "", "0,01 M"),
            ("Noir ériochrome T", "#2c3e50", "indicateur"),
            ("Solution tampon pH 10", "", ""),
            ("Acide calcon carboxylique", "", "indicateur"),
            ("Dichlorométhane", "", "solvant"),
            ("Acétate d'éthyle", "", "solvant"),
            ("Hexane", "", "solvant"),
            ("Huile d'olive", "#a3b18a", ""),
            ("Graines d'arachide", "", ""),
            ("Noix de coco", "", ""),
            ("Feuilles de menthe", "#588157", ""),
            ("Écorces d'agrumes", "#f4a261", ""),
            ("Pierre ponce", "", ""),
            ("Sel de cuisine", "", ""),
        ]
        result = {}
        for name, color, concentration in data:
            obj, _ = Reagent.objects.get_or_create(
                name=name,
                defaults={"color": color, "concentration": concentration},
            )
            result[name] = obj
        # pH connus de quelques solutions courantes (ordres de grandeur
        # scolaires). Renseigne uniquement les lignes encore vides pour
        # ne jamais écraser une valeur ajustée dans l'admin.
        known_ph = {
            "Solution de NaOH": 13.0,
            "Acide chlorhydrique (HCl)": -1.1,
            "Solution de HCl diluée": 1.0,
            "Hydroxyde de potassium (KOH)": 12.4,
            "Lait": 6.6,
            "Eau distillée": 7.0,
            "Eau de Javel": 11.5,
            "Solution tampon pH 10": 10.0,
        }
        for name, ph in known_ph.items():
            Reagent.objects.filter(name=name, ph__isnull=True).update(ph=ph)
        # Dangers SGH + conseils de manipulation (ordres de grandeur
        # scolaires). Ne remplit que les champs encore vides pour ne
        # jamais écraser un réglage affiné dans l'admin.
        known_hazards = {
            "Solution de NaOH": (
                ["GHS05"],
                "Gants et lunettes obligatoires. En cas de contact avec la peau, rincer abondamment à l'eau.",
            ),
            "Hydroxyde de sodium (NaOH) solide": (
                ["GHS05"],
                "Solide corrosif : gants et lunettes, éviter tout contact avec la peau.",
            ),
            "Soude caustique": (
                ["GHS05"],
                "Corrosif : gants et lunettes obligatoires.",
            ),
            "Acide chlorhydrique (HCl)": (
                ["GHS05"],
                "Acide concentré : manipuler sous hotte avec gants et lunettes.",
            ),
            "Solution de HCl diluée": (
                ["GHS05"],
                "Gants et lunettes recommandés.",
            ),
            "Acide sulfurique (H2SO4)": (
                ["GHS05"],
                "Acide concentré très corrosif : toujours verser l'acide dans l'eau, jamais l'inverse.",
            ),
            "Hydroxyde de potassium (KOH)": (
                ["GHS05"],
                "Gants et lunettes obligatoires.",
            ),
            "Permanganate de potassium (KMnO4)": (
                ["GHS03", "GHS07"],
                "Oxydant puissant : tenir éloigné des matières organiques et inflammables.",
            ),
            "Eau de Javel": (
                ["GHS05", "GHS09"],
                "Ne jamais mélanger avec un acide : dégagement de chlore toxique.",
            ),
            "Éthanol": (
                ["GHS02"],
                "Liquide inflammable : tenir éloigné des flammes.",
            ),
            "Éther diéthylique": (
                ["GHS02"],
                "Très inflammable et volatil : manipuler loin de toute flamme, sous hotte.",
            ),
        }
        for name, (codes, advice) in known_hazards.items():
            obj = result.get(name)
            if obj is None:
                continue
            changed = []
            if not obj.hazards:
                obj.hazards = ",".join(codes)
                changed.append("hazards")
            if not obj.safety_advice:
                obj.safety_advice = advice
                changed.append("safety_advice")
            if changed:
                obj.save(update_fields=changed)
        # Incompatibilités dangereuses (symétriques : un seul sens suffit).
        strong_bases = [
            "Solution de NaOH",
            "Hydroxyde de sodium (NaOH) solide",
            "Soude caustique",
            "Hydroxyde de potassium (KOH)",
            "Carbonate de sodium (Na2CO3)",
        ]
        strong_acids = [
            "Acide chlorhydrique (HCl)",
            "Solution de HCl diluée",
            "Acide sulfurique (H2SO4)",
        ]
        incompatibilities = {
            "Eau de Javel": strong_acids,
            "Permanganate de potassium (KMnO4)": ["Éthanol", "Éther diéthylique"],
        }
        for acid in strong_acids:
            incompatibilities.setdefault(acid, []).extend(strong_bases)
        for name, others in incompatibilities.items():
            obj = result.get(name)
            if obj is None:
                continue
            for other in dict.fromkeys(others):
                other_obj = result.get(other)
                if other_obj is not None:
                    obj.incompatible_with.add(other_obj)
        self.stdout.write(f"{len(result)} réactifs créés/vérifiés.")
        return result

    # ------------------------------------------------------------------
    # INDICATEURS
    # ------------------------------------------------------------------
    def create_indicators(self):
        data = [
            ("pH", "", "number"),
            ("Volume versé", "mL", "number"),
            ("Concentration obtenue", "mol/L", "number"),
            ("Masse obtenue", "g", "number"),
            ("Température", "°C", "number"),
            ("Temps", "min", "number"),
            ("Couleur de la solution", "", "color"),
            ("Rendement", "%", "number"),
            ("Degré Dornic", "°D", "number"),
            ("Degré chlorométrique", "°chl", "number"),
            ("Dureté de l'eau", "°f", "number"),
            ("Point de fusion", "°C", "number"),
            ("Précipité formé", "", "boolean"),
        ]
        result = {}
        for name, unit, value_type in data:
            obj, _ = Indicator.objects.get_or_create(
                name=name,
                defaults={"unit": unit, "value_type": value_type},
            )
            result[name] = obj
        self.stdout.write(f"{len(result)} indicateurs créés/vérifiés.")
        return result

    # ------------------------------------------------------------------
    # CATEGORIES DE REACTION
    # ------------------------------------------------------------------
    def create_reaction_types(self, ind):
        data = {
            "Acide-base": ["pH", "Volume versé", "Concentration obtenue", "Couleur de la solution"],
            "Oxydoréduction": ["Volume versé", "Concentration obtenue", "Couleur de la solution"],
            "Complexométrie": ["Volume versé", "Dureté de l'eau"],
            "Extraction liquide-liquide": ["Masse obtenue", "Couleur de la solution"],
            "Synthèse organique": ["Masse obtenue", "Rendement", "Point de fusion", "Température"],
            "Formulation chimique": ["Masse obtenue", "Température", "Couleur de la solution"],
            "Hydrodistillation": ["Masse obtenue", "Rendement", "Température"],
        }
        result = {}
        for name, indicator_names in data.items():
            obj, _ = ReactionType.objects.get_or_create(
                name=name, defaults={"slug": slugify(name)}
            )
            obj.default_indicators.set([ind[n] for n in indicator_names])
            result[name] = obj
        self.stdout.write(f"{len(result)} catégories de réaction créées/vérifiées.")
        return result

    # ------------------------------------------------------------------
    # EXPERIENCES
    # ------------------------------------------------------------------
    def create_experiments(self, mat, rea, ind, rtype):
        experiments = [
            dict(
                title="Préparation de solutions",
                short_description="Préparer une solution par dissolution et par dilution d'une solution mère.",
                level="easy",
                duration=20,
                reaction_type="Acide-base",
                materials=["Balance analytique", "Verre de montre", "Fiole jaugée", "Bécher", "Pipette graduée", "Pissette", "Spatule"],
                reagents=["Hydroxyde de sodium (NaOH) solide", "Eau distillée", "Acide chlorhydrique (HCl)", "Carbonate de sodium (Na2CO3)", "Éthanol"],
                steps=[
                    ("Peser le soluté", "Calculer et peser la masse nécessaire sans toucher le produit à mains nues."),
                    ("Dissoudre", "Introduire le soluté dans une fiole jaugée à moitié remplie d'eau distillée, agiter jusqu'à dissolution totale."),
                    ("Compléter au trait de jauge", "Ajouter de l'eau distillée jusqu'au trait de jauge et homogénéiser."),
                ],
            ),
            dict(
                title="Dosage acido-basique (étalonnage HCl)",
                short_description="Vérifier ou étalonner la concentration d'une solution d'acide chlorhydrique par titrage.",
                level="medium",
                duration=25,
                reaction_type="Acide-base",
                materials=["Burette", "Erlenmeyer", "Pipette graduée", "Statif", "Pince", "Bécher"],
                reagents=["Solution de HCl diluée", "Solution de NaOH", "Carbonate de sodium (Na2CO3)", "Bleu de bromothymol", "Méthyl-orange"],
                steps=[
                    ("Préparer la burette", "Rincer et remplir la burette avec la solution titrante."),
                    ("Préparer l'échantillon", "Introduire le volume à doser dans un erlenmeyer et ajouter quelques gouttes d'indicateur coloré."),
                    ("Titrer", "Verser la solution titrante goutte à goutte jusqu'au virage de l'indicateur, noter le volume équivalent."),
                ],
            ),
            dict(
                title="Dosage d'oxydoréduction (manganimétrie)",
                short_description="Déterminer la concentration des ions Fe2+ dans une solution de sulfate ferreux par dosage au permanganate.",
                level="advanced",
                duration=25,
                reaction_type="Oxydoréduction",
                materials=["Burette", "Erlenmeyer", "Pipette graduée", "Entonnoir"],
                reagents=["Sulfate ferreux (FeSO4)", "Permanganate de potassium (KMnO4)", "Acide sulfurique (H2SO4)", "Eau distillée"],
                steps=[
                    ("Préparer la burette", "Remplir la burette avec la solution de permanganate de potassium."),
                    ("Préparer l'échantillon", "Verser dans l'erlenmeyer le FeSO4, l'eau et l'acide sulfurique."),
                    ("Titrer jusqu'au virage", "Verser goutte à goutte le KMnO4 jusqu'à l'apparition d'une teinte rose persistante."),
                ],
            ),
            dict(
                title="Titrage de l'acidité totale d'un lait",
                short_description="Déterminer la fraîcheur d'un lait en mesurant son degré Dornic par dosage acido-basique.",
                level="medium",
                duration=20,
                reaction_type="Acide-base",
                materials=["Burette", "Erlenmeyer", "Pipette graduée", "Éprouvette graduée", "Pissette"],
                reagents=["Lait", "Hydroxyde de potassium (KOH)", "Phénolphtaléine", "Eau distillée"],
                steps=[
                    ("Préparer l'échantillon", "Prélever le lait, ajouter de l'eau distillée et quelques gouttes de phénolphtaléine."),
                    ("Titrer", "Verser la solution de KOH jusqu'à l'apparition d'une couleur rose persistante."),
                    ("Calculer le degré Dornic", "Utiliser le volume versé pour déterminer le degré Dornic et la fraîcheur du lait."),
                ],
            ),
            dict(
                title="Synthèse de l'aspirine",
                short_description="Synthétiser l'acide acétylsalicylique (aspirine) à partir d'acide salicylique et d'anhydride acétique.",
                level="advanced",
                duration=45,
                reaction_type="Synthèse organique",
                materials=["Ballon mono col rodé", "Réfrigérant", "Plaque chauffante avec agitation", "Büchner", "Étuve", "Bain-marie", "Erlenmeyer"],
                reagents=["Acide salicylique", "Anhydride acétique", "Acide sulfurique (H2SO4)", "Éthanol", "Eau distillée"],
                steps=[
                    ("Préparer le montage à reflux", "Introduire l'acide salicylique et l'anhydride acétique dans un ballon bien sec."),
                    ("Chauffer et catalyser", "Chauffer légèrement puis ajouter l'acide sulfurique sous agitation, maintenir au reflux 20 min."),
                    ("Filtrer et recristalliser", "Refroidir, filtrer sur Büchner, laver à l'eau glacée puis recristalliser dans l'éthanol."),
                ],
            ),
            dict(
                title="Dosage de l'aspirine dans un comprimé",
                short_description="Doser l'acide acétylsalicylique contenu dans un comprimé par pH-métrie ou colorimétrie.",
                level="medium",
                duration=30,
                reaction_type="Acide-base",
                materials=["Mortier", "Balance analytique", "Fiole jaugée", "Burette", "pH-mètre", "Agitateur magnétique", "Barreau aimanté", "Bécher"],
                reagents=["Comprimé d'aspirine", "Solution de NaOH", "Phénolphtaléine", "Eau distillée"],
                steps=[
                    ("Préparer la solution d'aspirine", "Broyer un comprimé et le dissoudre dans une fiole jaugée d'eau distillée tiède."),
                    ("Doser par pH-métrie", "Verser la soude en notant le pH à intervalles réguliers."),
                    ("Doser par colorimétrie", "Titrer un second prélèvement avec de la phénolphtaléine jusqu'au virage."),
                ],
            ),
            dict(
                title="Production et dosage de l'eau de Javel",
                short_description="Produire de l'eau de Javel puis doser ses ions hypochlorite par iodométrie.",
                level="advanced",
                duration=40,
                reaction_type="Oxydoréduction",
                materials=["Burette", "Erlenmeyer", "Pipette graduée", "Éprouvette graduée", "Seaux et agitateurs"],
                reagents=["Chlore (dichlore)", "Soude caustique", "Carbonate de sodium (Na2CO3)", "Iodure de potassium (KI)", "Thiosulfate de sodium", "Empois d'amidon (thiodène)", "Eau de Javel"],
                steps=[
                    ("Produire l'eau de Javel", "Dissoudre le chlore dans l'eau, ajouter la soude caustique puis le carbonate de sodium."),
                    ("Réduire les ions hypochlorite", "Ajouter l'iodure de potassium et de l'acide éthanoïque, observer l'apparition du diiode."),
                    ("Doser le diiode formé", "Titrer avec le thiosulfate de sodium jusqu'au virage, avec ajout d'empois d'amidon en fin de dosage."),
                ],
            ),
            dict(
                title="Dosage complexométrique du calcium et du magnésium (dureté de l'eau)",
                short_description="Déterminer la dureté totale, calcique et magnésienne d'une eau par dosage à l'EDTA.",
                level="advanced",
                duration=30,
                reaction_type="Complexométrie",
                materials=["Burette", "Fiole conique", "Pipette graduée"],
                reagents=["EDTA (acide éthylènediaminetétracétique)", "Noir ériochrome T", "Solution tampon pH 10", "Acide calcon carboxylique", "Solution de NaOH"],
                steps=[
                    ("Préparer l'échantillon", "Introduire l'eau à analyser dans une fiole conique avec la solution tampon et l'indicateur."),
                    ("Titrer à l'EDTA", "Verser l'EDTA jusqu'au virage du rouge/violet vers le bleu."),
                    ("Déterminer la dureté", "Calculer la dureté totale, puis répéter à pH élevé pour isoler la dureté calcique."),
                ],
            ),
            dict(
                title="Extraction liquide-liquide de colorants de fruits",
                short_description="Extraire le lycopène de la tomate et la bêta-carotène de la carotte par extraction liquide-liquide.",
                level="medium",
                duration=35,
                reaction_type="Extraction liquide-liquide",
                materials=["Mortier", "Ampoule à décanter", "Bécher", "Entonnoir"],
                reagents=["Hexane", "Acétate d'éthyle", "Eau distillée"],
                steps=[
                    ("Préparer le filtrat", "Broyer les fruits, ajouter de l'eau distillée et filtrer."),
                    ("Extraire", "Introduire le filtrat dans l'ampoule à décanter avec le solvant extracteur, agiter et séparer les phases."),
                    ("Récupérer le colorant", "Répéter l'extraction 2 fois et peser la masse de colorant obtenue."),
                ],
            ),
            dict(
                title="Extraction des huiles essentielles",
                short_description="Extraire l'huile essentielle d'agrumes ou de menthe par hydrodistillation.",
                level="advanced",
                duration=50,
                reaction_type="Hydrodistillation",
                materials=["Ballon mono col", "Réfrigérant", "Chauffe-ballon", "Ampoule à décanter", "Éprouvette graduée", "Évaporateur (Rotavapeur)"],
                reagents=["Écorces d'agrumes", "Feuilles de menthe", "Cyclohexane", "Éther diéthylique", "Eau distillée", "Chlorure de sodium (NaCl)"],
                steps=[
                    ("Préparer le montage", "Introduire les végétaux et l'eau dans le ballon, monter le dispositif d'hydrodistillation."),
                    ("Distiller", "Chauffer environ 30 minutes et recueillir le distillat."),
                    ("Extraire l'huile", "Extraire le distillat au solvant organique dans une ampoule à décanter, puis évaporer le solvant."),
                ],
            ),
            dict(
                title="Synthèse du savon (saponification)",
                short_description="Synthétiser un savon par saponification d'une huile végétale avec de la soude.",
                level="medium",
                duration=45,
                reaction_type="Synthèse organique",
                materials=["Ballon mono col", "Réfrigérant", "Plaque chauffante avec agitation", "Bécher", "Entonnoir"],
                reagents=["Huile alimentaire", "Huile d'olive", "Solution de NaOH", "Éthanol", "Chlorure de sodium (NaCl)", "Eau distillée"],
                steps=[
                    ("Saponifier", "Chauffer à reflux le mélange huile + soude + éthanol pendant 30 minutes."),
                    ("Relarguer", "Verser le mélange dans une solution saturée de chlorure de sodium, le savon précipite."),
                    ("Filtrer et sécher", "Filtrer, laver à l'eau glacée et laisser sécher le savon dans un moule."),
                ],
            ),
            dict(
                title="Production de savon liquide (détergent)",
                short_description="Formuler un détergent liquide par homogénéisation de plusieurs constituants.",
                level="easy",
                duration=40,
                reaction_type="Formulation chimique",
                materials=["Seaux et agitateurs"],
                reagents=["Texapon", "Carbonate de sodium (Na2CO3)", "Acide sulfurique (H2SO4)", "Sel de cuisine", "Colorant", "Parfum", "Eau distillée"],
                steps=[
                    ("Dissoudre le Texapon", "Dissoudre le texapon dans l'eau et laisser reposer."),
                    ("Ajouter les autres constituants", "Ajouter successivement le carbonate de sodium, le sel, puis le mélange eau/acide sulfurique en tournant à chaque étape."),
                    ("Finaliser", "Ajouter le colorant et le parfum, tourner puis laisser reposer 24h."),
                ],
            ),
            dict(
                title="Production d'huile végétale (coco / arachide)",
                short_description="Extraire l'huile de noix de coco ou de graines d'arachide par presse et solvant.",
                level="medium",
                duration=60,
                reaction_type="Formulation chimique",
                materials=["Presse / mixeur", "Tamis", "Casserole", "Bain-marie"],
                reagents=["Noix de coco", "Graines d'arachide", "Sel de cuisine", "Eau distillée"],
                steps=[
                    ("Préparer la matière première", "Toaster/râper les graines ou la chair de coco selon le produit."),
                    ("Extraire", "Broyer, mixer avec de l'eau chaude puis filtrer pour séparer le liquide."),
                    ("Séparer l'huile", "Faire bouillir le surnageant jusqu'à évaporation de l'eau et séparation de l'huile."),
                ],
            ),
        ]

        count = 0
        for exp in experiments:
            experiment, _ = Experiment.objects.get_or_create(
                slug=slugify(exp["title"])[:50],
                defaults={
                    "title": exp["title"],
                    "short_description": exp["short_description"],
                    "level": exp["level"],
                    "duration": exp["duration"],
                },
            )

            ExperimentConfig.objects.update_or_create(
                experiment=experiment,
                defaults={"reaction_type": rtype[exp["reaction_type"]]},
            )

            for order, name in enumerate(exp["materials"], start=1):
                ExperimentMaterial.objects.get_or_create(
                    experiment=experiment, material=mat[name], defaults={"order": order}
                )

            for order, name in enumerate(exp["reagents"], start=1):
                ExperimentReagent.objects.get_or_create(
                    experiment=experiment, reagent=rea[name], defaults={"order": order}
                )

            for number, (title, description) in enumerate(exp["steps"], start=1):
                ProtocolStep.objects.get_or_create(
                    experiment=experiment,
                    number=number,
                    defaults={"title": title, "description": description},
                )

            for order, name in enumerate(rtype[exp["reaction_type"]].default_indicators.all(), start=1):
                ExperimentIndicator.objects.get_or_create(
                    experiment=experiment, indicator=name, defaults={"order": order}
                )

            count += 1

        self.stdout.write(f"{count} expériences créées/vérifiées.")