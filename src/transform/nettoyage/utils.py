"""Helpers partages pour la couche de nettoyage.

Cette couche encapsule les regles transverses :
- nettoyage de texte ;
- evaluation du perimetre metier data / IA / BI / cloud ;
- normalisation de dates, salaires, contrats et URLs ;
- support a la deduplication.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import html
import math
import re
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlparse, urlunparse
import unicodedata

import pandas as pd


OFFER_SOURCE_NAMES = {
    "bpce",
    "france_travail",
    "region_ile_de_france",
    "welcome_to_the_jungle",
    "postgresql_history",
}
AGGREGATE_SOURCE_NAMES = {
    "hive_aggregates",
}

SOURCE_PRIORITY = {
    "welcome_to_the_jungle": 60,
    "bpce": 55,
    "france_travail": 50,
    "region_ile_de_france": 45,
    "postgresql_history": 30,
}

STRONG_ROLE_KEYWORDS = (
    "data engineer",
    "ingenieur data",
    "ingenieur donnees",
    "data scientist",
    "data analyst",
    "analyste data",
    "analyste donnees",
    "analytics engineer",
    "machine learning engineer",
    "ingenieur machine learning",
    "mlops engineer",
    "ingenieur mlops",
    "ai engineer",
    "developpeur ia",
    "developpeur intelligence artificielle",
    "data architect",
    "architecte data",
    "business intelligence",
    "analyste bi",
    "consultant data",
    "consultant bi",
    "data platform engineer",
    "cloud data engineer",
    "developpeur etl",
    "ingenieur etl",
    "developpeur big data",
    "ingenieur big data",
    "dbt developer",
    "dataops",
    "llm engineer",
    "nlp engineer",
    "computer vision engineer",
)

FOCUS_KEYWORDS = (
    "data",
    "donnees",
    "database",
    "base de donnees",
    "bdd",
    "analytics",
    "analytique",
    "reporting",
    "decisionnel",
    "machine learning",
    "deep learning",
    "business intelligence",
    "etl",
    "ia",
    "ai",
    "mlops",
    "cloud",
    "big data",
    "dbt",
    "airflow",
    "databricks",
    "snowflake",
    "spark",
    "kafka",
    "power bi",
    "tableau",
    "looker",
    "nlp",
    "llm",
    "computer vision",
)

SUPPORT_TECH_KEYWORDS = (
    "python",
    "sql",
    "spark",
    "pyspark",
    "snowflake",
    "databricks",
    "airflow",
    "dbt",
    "kafka",
    "aws",
    "azure",
    "gcp",
    "power bi",
    "tableau",
    "looker",
    "mlflow",
    "terraform",
    "docker",
    "kubernetes",
    "scala",
    "pandas",
)

CONTRACT_TYPE_ALIASES = {
    "cdi": "cdi",
    "cdd": "cdd",
    "freelance": "freelance",
    "interim": "interim",
    "stage": "stage",
    "alternance": "alternance",
    "apprentissage": "alternance",
    "contrat apprentissage": "alternance",
    "contrat professionnalisation": "alternance",
    "professionnalisation": "alternance",
    "temps plein": "temps plein",
    "temps partiel": "temps partiel",
}

GENERIC_TITLE_STOPWORDS = {
    "h",
    "f",
    "hf",
    "h f",
    "h/f",
    "fh",
    "the",
    "de",
    "du",
    "des",
    "la",
    "le",
    "les",
    "d",
    "l",
    "en",
    "et",
    "pour",
    "with",
    "a",
    "to",
    "of",
    "senior",
    "junior",
    "alternance",
    "stage",
}

SALARY_RANGE_PATTERN = re.compile(
    r"(?P<first>\d+(?:[.,]\d+)?)\s*(?P<first_k>[kK])?"
    r"\s*(?:a|à|-|to)\s*"
    r"(?P<second>\d+(?:[.,]\d+)?)\s*(?P<second_k>[kK])?"
)
SALARY_SINGLE_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*([kK])?")


def nettoyer_texte(value: Any) -> str:
    """Nettoyer une valeur heterogene en texte lisible."""

    if value is None:
        return ""

    texte = html.unescape(str(value))
    texte = texte.replace("\xa0", " ")
    texte = re.sub(r"\s+", " ", texte)
    return texte.strip()


def normaliser_texte_match(value: Any) -> str:
    """Normaliser un texte pour la comparaison souple."""

    texte = nettoyer_texte(value).casefold()
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(car for car in texte if not unicodedata.combining(car))
    texte = re.sub(r"[^a-z0-9+/&\s-]", " ", texte)
    texte = re.sub(r"\s+", " ", texte)
    return texte.strip()


def decouper_texte_signature(value: Any, max_tokens: int = 6) -> str:
    """Construire une signature compacte a partir des mots significatifs."""

    tokens = [
        token
        for token in normaliser_texte_match(value).split()
        if token and token not in GENERIC_TITLE_STOPWORDS and len(token) > 1
    ]
    return " ".join(tokens[:max_tokens])


def normaliser_url(value: Any) -> str:
    """Produire une URL canonique stable pour les comparaisons."""

    url = nettoyer_texte(value)
    if not url:
        return ""

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url

    path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            "",
            "",
        )
    )


def normaliser_liste_competences(raw_value: Any) -> list[str]:
    """Nettoyer et dedoublonner une liste de competences."""

    if raw_value is None:
        return []

    candidats: list[str] = []
    if isinstance(raw_value, list):
        for element in raw_value:
            texte = nettoyer_texte(element)
            if texte:
                candidats.append(texte)
    else:
        texte = nettoyer_texte(raw_value)
        if texte:
            separateurs = re.split(r"[;,|/]+", texte)
            for element in separateurs:
                propre = nettoyer_texte(element)
                if propre:
                    candidats.append(propre)

    vues: set[str] = set()
    competences: list[str] = []
    for element in candidats:
        cle = normaliser_texte_match(element)
        if not cle or cle in vues:
            continue
        vues.add(cle)
        competences.append(element)

    return competences


def normaliser_type_contrat(value: Any) -> str:
    """Ramener les contrats vers un petit vocabulaire stable."""

    texte = normaliser_texte_match(value)
    if not texte:
        return ""

    for alias, normalise in CONTRACT_TYPE_ALIASES.items():
        if alias in texte:
            return normalise

    return nettoyer_texte(value)


def normaliser_teletravail(value: Any) -> str:
    """Normaliser grossierement le signal teletravail."""

    texte = normaliser_texte_match(value)
    if not texte:
        return ""

    if "full remote" in texte or "100% remote" in texte or "teletravail total" in texte:
        return "remote"
    if "teletravail" in texte or "remote" in texte or "hybride" in texte:
        return "hybrid"
    if "sur site" in texte or "presentiel" in texte:
        return "onsite"
    return nettoyer_texte(value)


def convertir_vers_datetime_iso(raw_value: Any) -> tuple[str, str]:
    """Convertir une valeur date/heure vers ISO + date simple."""

    texte = nettoyer_texte(raw_value)
    if not texte:
        return "", ""

    relatifs = {
        "aujourd'hui": 0,
        "aujourdhui": 0,
        "hier": 1,
        "avant-hier": 2,
        "avant hier": 2,
    }
    texte_normalise = normaliser_texte_match(texte)
    if texte_normalise in relatifs:
        valeur = datetime.now(timezone.utc) - timedelta(days=relatifs[texte_normalise])
        return valeur.isoformat(), valeur.date().isoformat()

    try:
        utilise_dayfirst = not bool(re.match(r"^\d{4}-\d{2}-\d{2}", texte))
        parsed = pd.to_datetime(
            texte,
            utc=True,
            dayfirst=utilise_dayfirst,
            errors="coerce",
        )
    except Exception:
        return "", ""

    if parsed is None or pd.isna(parsed):
        return "", ""

    valeur = parsed.to_pydatetime()
    return valeur.isoformat(), valeur.date().isoformat()


def _convertir_nombre_salaire(nombre: str, suffixe_k: str | None) -> float | None:
    """Convertir un nombre brut de salaire en borne exploitable."""

    try:
        valeur = float(nombre.replace(",", "."))
    except ValueError:
        return None

    if suffixe_k:
        valeur *= 1000
    return valeur


def normaliser_valeur_numerique(value: Any) -> float | None:
    """Normaliser une borne numerique de salaire si possible."""

    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)

    texte = nettoyer_texte(value)
    if not texte:
        return None

    correspondance = SALARY_SINGLE_PATTERN.search(texte)
    if not correspondance:
        return None

    return _convertir_nombre_salaire(
        correspondance.group(1),
        correspondance.group(2),
    )


def extraire_infos_salaire(offre: dict[str, Any]) -> dict[str, Any]:
    """Consolider les informations de salaire dans une structure comparable."""

    salaire_texte = nettoyer_texte(offre.get("salary"))
    salaire_min = normaliser_valeur_numerique(offre.get("salary_min"))
    salaire_max = normaliser_valeur_numerique(offre.get("salary_max"))
    raw_payload = offre.get("raw_payload") if isinstance(offre.get("raw_payload"), dict) else {}
    salaire_pred = offre.get("salary_is_predicted")

    if salaire_min is None or salaire_max is None:
        correspondance_plage = SALARY_RANGE_PATTERN.search(salaire_texte)
        if correspondance_plage:
            premiere = _convertir_nombre_salaire(
                correspondance_plage.group("first"),
                correspondance_plage.group("first_k"),
            )
            seconde = _convertir_nombre_salaire(
                correspondance_plage.group("second"),
                correspondance_plage.group("second_k"),
            )
            if salaire_min is None:
                salaire_min = premiere
            if salaire_max is None:
                salaire_max = seconde
        elif salaire_texte and (salaire_min is None and salaire_max is None):
            unique = normaliser_valeur_numerique(salaire_texte)
            salaire_min = unique
            salaire_max = unique

    if salaire_min is not None and salaire_max is not None and salaire_min > salaire_max:
        salaire_min, salaire_max = salaire_max, salaire_min

    salaire_currency = nettoyer_texte(raw_payload.get("salary_currency"))
    if not salaire_currency:
        texte_match = normaliser_texte_match(salaire_texte)
        if "€" in salaire_texte or "euro" in texte_match or "euros" in texte_match:
            salaire_currency = "EUR"

    salaire_period = nettoyer_texte(raw_payload.get("salary_period"))
    texte_match = normaliser_texte_match(salaire_texte)
    if not salaire_period:
        if any(marqueur in texte_match for marqueur in ("mensuel", "mois", "monthly", "/month")):
            salaire_period = "monthly"
        elif any(marqueur in texte_match for marqueur in ("annuel", "an", "year", "yearly", "annum")):
            salaire_period = "yearly"
        elif "k" in salaire_texte and salaire_min and salaire_min >= 1000:
            salaire_period = "yearly"

    return {
        "salary": salaire_texte,
        "salary_min_normalized": salaire_min,
        "salary_max_normalized": salaire_max,
        "salary_currency": salaire_currency,
        "salary_period": salaire_period,
        "salary_is_predicted": bool(salaire_pred) if salaire_pred is not None else False,
    }


def compter_mots_cles(texte: str, mots_cles: tuple[str, ...]) -> int:
    """Compter les mots-cles distincts presents dans un texte normalise."""

    score = 0
    for mot_cle in mots_cles:
        motif = r"(?<![a-z0-9])" + re.escape(mot_cle).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
        if re.search(motif, texte):
            score += 1
    return score


def evaluer_perimetre_metier(offre: dict[str, Any]) -> tuple[bool, int, list[str]]:
    """Evaluer si une offre entre dans le perimetre data / IA / BI / cloud."""

    if offre.get("source") in AGGREGATE_SOURCE_NAMES:
        return True, 999, ["aggregate_source"]

    champs_titre = " ".join(
        nettoyer_texte(offre.get(cle))
        for cle in ("title", "job_family", "job_label", "category", "domaine", "filiere", "speciality")
    )
    description = nettoyer_texte(offre.get("description"))
    competences = " ".join(normaliser_liste_competences(offre.get("skills")))
    texte_titre = normaliser_texte_match(champs_titre)
    texte_long = normaliser_texte_match(" ".join((champs_titre, description, competences)))

    score = 0
    raisons: list[str] = []

    role_hits_titre = compter_mots_cles(texte_titre, STRONG_ROLE_KEYWORDS)
    if role_hits_titre:
        score += 6
        raisons.append("role_keyword_title")

    focus_hits_titre = compter_mots_cles(texte_titre, FOCUS_KEYWORDS)
    if focus_hits_titre:
        score += min(3, focus_hits_titre)
        raisons.append("focus_keyword_title")

    support_hits_titre = compter_mots_cles(texte_titre, SUPPORT_TECH_KEYWORDS)
    if support_hits_titre:
        score += 1
        raisons.append("tech_keyword_title")

    focus_hits_global = compter_mots_cles(texte_long, FOCUS_KEYWORDS)
    if focus_hits_global >= 2:
        score += 2
        raisons.append("focus_keyword_body")

    support_hits = compter_mots_cles(texte_long, SUPPORT_TECH_KEYWORDS)
    if support_hits >= 2:
        score += 2
        raisons.append("tech_keyword_body")

    if description and len(description) >= 250 and focus_hits_global:
        score += 1
        raisons.append("descriptive_offer")

    titre = nettoyer_texte(offre.get("title"))
    description_presente = bool(description)
    if not titre and not description_presente:
        return False, score, ["missing_title_and_description"]

    titre_ancre = role_hits_titre > 0 or focus_hits_titre > 0
    if role_hits_titre > 0:
        return True, score, raisons
    if titre_ancre and (focus_hits_global >= 2 or support_hits >= 1):
        return True, score, raisons
    if support_hits_titre > 0 and focus_hits_global >= 2:
        return True, score, raisons

    return False, score, raisons


def calculer_completeness_score(offre: dict[str, Any]) -> int:
    """Mesurer la richesse utile d'une offre pour arbitrer les doublons."""

    score = 0
    champs_ponderes = {
        "external_id": 2,
        "title": 3,
        "company_name": 2,
        "location_label": 2,
        "published_at": 2,
        "url": 2,
        "description": 3,
        "contract_type": 1,
    }

    for cle, poids in champs_ponderes.items():
        if nettoyer_texte(offre.get(cle)):
            score += poids

    if offre.get("skills_normalized"):
        score += min(3, len(offre["skills_normalized"]))
    if offre.get("salary_min_normalized") is not None or offre.get("salary_max_normalized") is not None:
        score += 2
    if offre.get("salary_is_predicted"):
        score -= 1

    return score


def construire_blocs_deduplication(offre: dict[str, Any]) -> set[str]:
    """Construire des cles de blocage pour limiter les comparaisons."""

    blocs: set[str] = set()
    if offre.get("url_canonical"):
        blocs.add(f"url:{offre['url_canonical']}")

    title_sig = offre.get("title_signature") or ""
    company_sig = offre.get("company_signature") or ""
    location_sig = offre.get("location_signature") or ""
    published_date = offre.get("published_date") or ""

    if title_sig and company_sig:
        blocs.add(f"title_company:{title_sig}|{company_sig}")
    if title_sig and published_date:
        blocs.add(f"title_date:{title_sig}|{published_date}")
    if company_sig and published_date:
        blocs.add(f"company_date:{company_sig}|{published_date}")
    if title_sig and location_sig:
        blocs.add(f"title_location:{title_sig}|{location_sig}")

    return blocs


def similarite_texte(a: str, b: str) -> float:
    """Mesurer la similarite de deux textes deja normalises."""

    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def sont_doublons(offre_a: dict[str, Any], offre_b: dict[str, Any]) -> bool:
    """Determiner si deux offres normalisees representent la meme annonce."""

    url_a = offre_a.get("url_canonical") or ""
    url_b = offre_b.get("url_canonical") or ""
    if url_a and url_b and url_a == url_b:
        return True

    title_a = offre_a.get("title_signature") or offre_a.get("title_normalized") or ""
    title_b = offre_b.get("title_signature") or offre_b.get("title_normalized") or ""
    company_a = offre_a.get("company_signature") or offre_a.get("company_normalized") or ""
    company_b = offre_b.get("company_signature") or offre_b.get("company_normalized") or ""
    location_a = offre_a.get("location_signature") or ""
    location_b = offre_b.get("location_signature") or ""
    published_date_a = offre_a.get("published_date") or ""
    published_date_b = offre_b.get("published_date") or ""

    if title_a and title_b and company_a and company_b:
        if title_a == title_b and company_a == company_b:
            if published_date_a and published_date_b and published_date_a == published_date_b:
                return True
            if location_a and location_b and location_a == location_b:
                return True

    title_ratio = similarite_texte(
        offre_a.get("title_normalized") or title_a,
        offre_b.get("title_normalized") or title_b,
    )
    company_ratio = similarite_texte(
        offre_a.get("company_normalized") or company_a,
        offre_b.get("company_normalized") or company_b,
    )
    location_ratio = similarite_texte(location_a, location_b)
    dates_compatibles = not published_date_a or not published_date_b or published_date_a == published_date_b

    if title_ratio >= 0.97 and company_ratio >= 0.94 and (location_ratio >= 0.85 or dates_compatibles):
        return True

    if title_ratio >= 0.94 and company_ratio == 1.0 and location_ratio >= 0.9 and dates_compatibles:
        return True

    return False


def fusionner_competences(*listes: list[str]) -> list[str]:
    """Fusionner plusieurs listes de competences sans doublon."""

    vues: set[str] = set()
    resultat: list[str] = []
    for liste in listes:
        for competence in liste:
            texte = nettoyer_texte(competence)
            cle = normaliser_texte_match(texte)
            if not texte or not cle or cle in vues:
                continue
            vues.add(cle)
            resultat.append(texte)
    return resultat


def choisir_meilleur_texte(courant: Any, candidat: Any) -> str:
    """Conserver le texte le plus informatif."""

    texte_courant = nettoyer_texte(courant)
    texte_candidat = nettoyer_texte(candidat)
    if not texte_courant:
        return texte_candidat
    if not texte_candidat:
        return texte_courant
    return texte_candidat if len(texte_candidat) > len(texte_courant) else texte_courant
