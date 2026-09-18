"""Service d'intégration de l'API publique PubChem PUG REST.

PubChem sert uniquement de source d'informations chimiques (métadonnées
d'un composé). Il n'est jamais utilisé comme moteur de simulation : les
grandeurs physico-chimiques sont calculées par l'application Django.

L'accès à l'API ne nécessite aucune clé. Toutes les erreurs sont capturées
ici afin de ne jamais faire planter l'application : composé introuvable,
limite de requêtes (429), délai dépassé, réponse inattendue ou invalide.
"""

import logging
import re

import requests
from django.core.cache import cache
from urllib.parse import quote

logger = logging.getLogger(__name__)

PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUG_VIEW = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"
TIMEOUT = 8  # secondes
CACHE_TTL = 24 * 3600  # un jour
RESULTS_PER_SEARCH = 8

# Pictogrammes SGH reconnus (codes extraits des URL .../images/ghs/GHSxx.svg).
_KNOWN_GHS_CODES = frozenset({f"GHS{i:02d}" for i in range(1, 10)})
_PICTOGRAM_URL_RE = re.compile(r"/ghs/(GHS\d{2})\.svg", re.IGNORECASE)

# Propriétés demandées à PubChem pour chaque composé.
_PROPERTIES = ",".join(
    [
        "IUPACName",
        "MolecularFormula",
        "MolecularWeight",
        "CanonicalSMILES",
        "IsomericSMILES",
        "InChI",
        "InChIKey",
    ]
)


class PubChemError(Exception):
    """Erreur de communication avec PubChem (hors « introuvable »)."""


class PubChemNotFound(Exception):
    """Aucun composé ne correspond à la recherche."""


class PubChemRateLimited(Exception):
    """Limite de requêtes atteinte côté PubChem."""


def image_url(cid):
    """URL de la structure 2D (image PNG générée par PubChem)."""
    return f"{PUG}/compound/cid/{cid}/PNG"


def _quote(value):
    return quote(value.strip(), safe="")


def _get(url, timeout=TIMEOUT):
    """Appelle PubChem et lève une exception typée selon le statut."""
    try:
        response = requests.get(url, timeout=timeout)
    except requests.Timeout:
        raise PubChemError("délai de réponse dépassé")
    except requests.RequestException as exc:
        raise PubChemError(f"connexion impossible ({exc.__class__.__name__})")

    if response.status_code == 429:
        raise PubChemRateLimited()
    if response.status_code in (400, 404):
        raise PubChemNotFound()
    if response.status_code != 200:
        raise PubChemError(f"réponse inattendue (HTTP {response.status_code})")

    try:
        return response.json()
    except ValueError:
        raise PubChemError("réponse JSON invalide")


def search_compounds(name):
    """Recherche un composé par nom ; renvoie la liste des candidats.

    Un nom de composé peut être ambigu (plusieurs résultats). Chaque
    candidat est donc un dictionnaire : {cid, name, formula, weight,
    image_url}. Le résultat est mis en cache un jour pour ne pas
    re-solliciter l'API à chaque affichage.
    """
    key = f"pubchem:search:{name.strip().lower().replace(' ', '_')}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    payload = _get(f"{PUG}/compound/name/{_quote(name)}/cids/JSON")
    cid_list = (payload.get("IdentifierList") or {}).get("CID") or []
    cid_list = cid_list[:RESULTS_PER_SEARCH]

    if not cid_list:
        cache.set(key, [], CACHE_TTL)
        return []

    properties = {}
    try:
        payload = _get(
            f"{PUG}/compound/cid/{','.join(map(str, cid_list))}/property/{_PROPERTIES}/JSON"
        )
        for item in (payload.get("PropertyTable") or {}).get("Properties") or []:
            properties[item.get("CID")] = item
    except PubChemNotFound:
        # Un CID de la liste n'est pas résolu : on renvoie quand même les
        # candidats dont on a pu lire les propriétés (case rare).
        pass

    results = []
    for cid in cid_list:
        props = properties.get(cid, {})
        results.append(
            {
                "cid": cid,
                "name": props.get("IUPACName") or f"Composé PubChem #{cid}",
                "formula": props.get("MolecularFormula", ""),
                "weight": props.get("MolecularWeight"),
                "image_url": image_url(cid),
            }
        )

    cache.set(key, results, CACHE_TTL)
    return results


def get_compound_details(cid):
    """Renvoie les informations détaillées d'un composé (si disponible)."""
    payload = _get(f"{PUG}/compound/cid/{cid}/property/{_PROPERTIES}/JSON")
    properties = next(
        iter((payload.get("PropertyTable") or {}).get("Properties") or []), {}
    )
    if not properties:
        raise PubChemNotFound()

    synonyms = []
    try:
        syn_payload = _get(f"{PUG}/compound/cid/{cid}/synonyms/JSON")
        infos = (syn_payload.get("InformationList") or {}).get("Information") or []
        if infos:
            synonyms = infos[0].get("Synonym", [])
    except (PubChemError, PubChemNotFound):
        pass  # les synonymes sont facultatifs

    return {
        "cid": cid,
        "name": properties.get("IUPACName") or "",
        "formula": properties.get("MolecularFormula", ""),
        "weight": properties.get("MolecularWeight"),
        "canonical_smiles": properties.get("CanonicalSMILES", ""),
        "isomeric_smiles": properties.get("IsomericSMILES", ""),
        "inchi": properties.get("InChI", ""),
        "inchikey": properties.get("InChIKey", ""),
        "synonyms": synonyms[:12],
        "image_url": image_url(cid),
    }


def get_ghs_data(cid):
    """Pictogrammes SGH + mentions de danger d'un composé (source PubChem).

    Appelé une seule fois à l'import du composé : le résultat est mis en
    cache puis stocké en base, pour que les alertes restent disponibles
    hors-ligne au moment des manipulations. Renvoie toujours un
    dictionnaire {"pictograms": [...], "statements": [...]}, éventuellement
    vide (composé introuvable ou sans classification GHS).
    """
    key = f"pubchem:ghs:{cid}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        payload = _get(f"{PUG_VIEW}/data/compound/{cid}/JSON?heading=GHS+Classification")
    except PubChemNotFound:
        result = {"pictograms": [], "statements": []}
        cache.set(key, result, CACHE_TTL)
        return result

    pictograms = []
    statements = []

    def walk(sections):
        for section in sections or []:
            if section.get("TOCHeading") == "GHS Classification":
                for info in section.get("Information") or []:
                    values = ((info.get("Value") or {}).get("StringWithMarkup")) or []
                    if info.get("Name") == "Pictogram(s)":
                        for item in values:
                            for mark in item.get("Markup") or []:
                                match = _PICTOGRAM_URL_RE.search(mark.get("URL") or "")
                                if match:
                                    code = match.group(1).upper()
                                    if code in _KNOWN_GHS_CODES and code not in pictograms:
                                        pictograms.append(code)
                    elif info.get("Name") == "GHS Hazard Statements":
                        for item in values:
                            text = (item.get("String") or "").strip()
                            if text and text not in statements:
                                statements.append(text)
            walk(section.get("Section"))

    walk((payload.get("Record") or {}).get("Section"))

    result = {"pictograms": pictograms, "statements": statements[:8]}
    cache.set(key, result, CACHE_TTL)
    return result