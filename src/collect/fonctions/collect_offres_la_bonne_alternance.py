"""Module de collecte des offres La bonne alternance.

Ce module a pour responsabilites :
- appeler l'endpoint officiel d'export des offres La bonne alternance ;
- telecharger le JSON d'export journalier ;
- filtrer les opportunites pour ne garder que les vraies offres d'emploi ;
- recentrer la collecte sur le perimetre data / IA / BI / cloud du projet ;
- mapper les opportunites retenues vers le schema brut d'offre du projet.

Source officielle retenue :
- documentation generale : https://www.data.gouv.fr/dataservices/api-la-bonne-alternance
- espace developpeurs : https://api.apprentissage.beta.gouv.fr/fr/explorer/recherche-offre
- export des offres : GET /api/job/v1/export

Note importante :
- cette API est ouverte sur jeton et reservee a des usages non lucratifs ;
- le collecteur n'ecrit pas lui-meme en base PostgreSQL ;
- il prepare simplement des offres brutes reutilisables ensuite dans le pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import unicodedata
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - repli simple si la dependance manque
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LBA_EXPORT_ENDPOINT = "https://api.apprentissage.beta.gouv.fr/api/job/v1/export"
DEFAULT_LBA_TIMEOUT_SECONDS = 120
DEFAULT_LBA_ONLY_DIRECT_OFFERS = False
DEFAULT_LBA_ENABLE_KEYWORD_FILTER = True
DEFAULT_LBA_INCLUDE_RECRUITER_OPPORTUNITIES = False

DEFAULT_LBA_DATA_KEYWORDS = (
    "data engineer",
    "ingenieur donnees",
    "ingenieur data",
    "data pipeline",
    "etl developpeur",
    "developpeur etl",
    "ingenieur etl",
    "data integration",
    "integration donnees",
    "dataops",
    "developpeur intelligence artificielle",
    "developpeur ia",
    "machine learning engineer",
    "ingenieur machine learning",
    "ml engineer",
    "mlops",
    "mlops engineer",
    "ingenieur mlops",
    "deep learning",
    "nlp engineer",
    "computer vision engineer",
    "ingenieur nlp",
    "llm engineer",
    "ai engineer",
    "data scientist",
    "analyste donnees",
    "analyste data",
    "data analyst",
    "business analyst data",
    "statisticien donnees",
    "scientist donnees",
    "analyste decisionnel",
    "analyste bi",
    "business intelligence",
    "architecte data",
    "data architect",
    "cloud data engineer",
    "ingenieur cloud donnees",
    "architecte cloud",
    "data platform engineer",
    "ingenieur plateforme donnees",
    "aws data",
    "azure data",
    "gcp data",
    "databricks",
    "snowflake",
    "chef de projet data",
    "responsable data",
    "lead data",
    "consultant data",
    "consultant bi",
    "consultant decisionnel",
    "developpeur python data",
    "developpeur python ia",
    "ingenieur analytique",
    "ingenieur decisionnel",
    "developpeur big data",
    "ingenieur big data",
    "spark engineer",
    "ingenieur spark",
    "kafka engineer",
    "airflow",
    "dbt developer",
    "developpeur dbt",
    "apache spark",
    "apache kafka",
    "apache airflow",
    "dbt",
    "apache nifi",
    "elasticsearch data",
    "power bi",
    "tableau",
    "looker",
    "grafana data",
    "python",
    "sql",
)


def charger_variables_environnement_locales() -> None:
    """Charger `.env` si `python-dotenv` est disponible."""

    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")


def lire_booleen_lba(raw_value: Any, default: bool) -> bool:
    """Convertir proprement une valeur heterogene en booleen."""

    if raw_value is None:
        return default

    if isinstance(raw_value, bool):
        return raw_value

    texte = str(raw_value).strip().lower()
    if not texte:
        return default

    if texte in {"1", "true", "vrai", "yes", "oui", "on"}:
        return True

    if texte in {"0", "false", "faux", "no", "non", "off"}:
        return False

    return default


def normaliser_texte_lba(value: Any) -> str:
    """Normaliser un texte pour les comparaisons de mots-cles."""

    if value is None:
        return ""

    texte = str(value)
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(character for character in texte if not unicodedata.combining(character))
    texte = " ".join(texte.lower().split())
    return texte


def lire_cle_profonde_lba(item: Any, *path: str) -> Any:
    """Lire une cle profonde dans un dictionnaire imbrique."""

    current = item
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def lire_premiere_cle_profonde_lba(
    item: dict[str, Any],
    *candidate_paths: tuple[str, ...],
) -> Any:
    """Retourner la premiere valeur non vide trouvee parmi plusieurs chemins."""

    for path in candidate_paths:
        valeur = lire_cle_profonde_lba(item, *path)
        if valeur is None:
            continue

        if isinstance(valeur, str):
            if valeur.strip():
                return valeur.strip()
            continue

        if isinstance(valeur, list):
            if valeur:
                return valeur
            continue

        return valeur

    return None


def construire_headers_lba(api_key: str) -> dict[str, str]:
    """Construire les en-tetes HTTP utilises pour l'API LBA.

    L'espace developpeurs documente une autorisation de type `api-key`.
    Pour maximiser la compatibilite pratique, on envoie aussi un header
    `Authorization` standard, ignore si inutile par le serveur.
    """

    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "JobRadar-IA/1.0",
        "X-API-Key": api_key,
    }


def demander_url_export_lba(
    api_key: str,
    export_endpoint: str = DEFAULT_LBA_EXPORT_ENDPOINT,
    timeout_seconds: int = DEFAULT_LBA_TIMEOUT_SECONDS,
) -> tuple[str, str]:
    """Demander l'URL presignee du dernier export LBA."""

    response = requests.get(
        export_endpoint,
        headers=construire_headers_lba(api_key),
        timeout=timeout_seconds,
    )
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("LBA: la reponse de l'endpoint d'export n'est pas un objet JSON.")

    download_url = str(payload.get("url") or "").strip()
    last_update = str(payload.get("lastUpdate") or "").strip()
    if not download_url:
        raise ValueError("LBA: l'endpoint d'export ne fournit aucune URL de telechargement.")

    return download_url, last_update


def telecharger_export_lba(
    download_url: str,
    timeout_seconds: int = DEFAULT_LBA_TIMEOUT_SECONDS,
) -> Any:
    """Telecharger le JSON d'export LBA depuis l'URL presignee."""

    response = requests.get(
        download_url,
        headers={"Accept": "application/json", "User-Agent": "JobRadar-IA/1.0"},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def extraire_opportunites_export_lba(export_payload: Any) -> list[dict[str, Any]]:
    """Extraire la liste des opportunites depuis le JSON d'export."""

    if isinstance(export_payload, list):
        return [item for item in export_payload if isinstance(item, dict)]

    if isinstance(export_payload, dict):
        for key in ("data", "results", "items"):
            valeur = export_payload.get(key)
            if isinstance(valeur, list):
                return [item for item in valeur if isinstance(item, dict)]

    return []


def construire_liste_competences_lba(raw_value: Any) -> list[str]:
    """Transformer differents formats de competences en liste simple."""

    if raw_value is None:
        return []

    if isinstance(raw_value, list):
        competences = []
        for element in raw_value:
            texte = str(element or "").strip()
            if texte and texte not in competences:
                competences.append(texte)
        return competences

    texte = str(raw_value).strip()
    if not texte:
        return []

    fragments = []
    for separator in ("\n", ";", ","):
        if separator in texte:
            for fragment in texte.split(separator):
                valeur = fragment.strip(" -\t\r\n")
                if valeur and valeur not in fragments:
                    fragments.append(valeur)
            if fragments:
                return fragments

    return [texte]


def convertir_valeur_lba_vers_texte(raw_value: Any) -> str:
    """Convertir proprement une valeur heterogene en texte lisible."""

    if raw_value is None:
        return ""

    if isinstance(raw_value, list):
        valeurs = [str(element).strip() for element in raw_value if str(element or "").strip()]
        return ", ".join(valeurs)

    if isinstance(raw_value, bool):
        return "true" if raw_value else "false"

    return str(raw_value).strip()


def construire_competences_lba(item: dict[str, Any]) -> list[str]:
    """Construire une liste unifiee de competences / qualites."""

    competences: list[str] = []

    for raw_block in (
        lire_premiere_cle_profonde_lba(item, ("offer", "desired_skills")),
        lire_premiere_cle_profonde_lba(item, ("offer", "to_be_acquired_skills")),
    ):
        for competence in construire_liste_competences_lba(raw_block):
            if competence not in competences:
                competences.append(competence)

    return competences


def construire_texte_recherche_lba(item: dict[str, Any]) -> str:
    """Construire un texte de recherche large pour le filtrage metier."""

    blocs: list[str] = []

    for valeur in (
        lire_premiere_cle_profonde_lba(item, ("offer", "title")),
        lire_premiere_cle_profonde_lba(item, ("offer", "description")),
        lire_premiere_cle_profonde_lba(item, ("offer", "access_conditions")),
        lire_premiere_cle_profonde_lba(item, ("offer", "target_diploma")),
        lire_premiere_cle_profonde_lba(item, ("workplace", "name")),
        lire_premiere_cle_profonde_lba(item, ("workplace", "brand")),
        lire_premiere_cle_profonde_lba(item, ("workplace", "legal_name")),
    ):
        if valeur:
            blocs.append(str(valeur))

    rome_codes = lire_premiere_cle_profonde_lba(item, ("offer", "rome_codes"))
    if isinstance(rome_codes, list):
        blocs.extend(str(code) for code in rome_codes if str(code or "").strip())

    blocs.extend(construire_competences_lba(item))

    return normaliser_texte_lba(" ".join(blocs))


def correspond_au_perimetre_data_lba(
    item: dict[str, Any],
    keywords: tuple[str, ...] = DEFAULT_LBA_DATA_KEYWORDS,
) -> bool:
    """Verifier si une opportunite LBA correspond au perimetre metier vise."""

    texte = construire_texte_recherche_lba(item)
    if not texte:
        return False

    return any(keyword in texte for keyword in keywords)


def construire_identifiant_lba(item: dict[str, Any]) -> str:
    """Construire un identifiant stable pour l'offre LBA."""

    identifiant = lire_premiere_cle_profonde_lba(
        item,
        ("identifier", "id"),
        ("identifier", "partner_job_id"),
        ("id",),
    )
    if identifiant:
        return str(identifiant).strip()

    empreinte_source = " | ".join(
        fragment
        for fragment in (
            str(lire_premiere_cle_profonde_lba(item, ("identifier", "partner_label")) or "").strip(),
            str(lire_premiere_cle_profonde_lba(item, ("offer", "title")) or "").strip(),
            str(lire_premiere_cle_profonde_lba(item, ("workplace", "name")) or "").strip(),
            str(lire_premiere_cle_profonde_lba(item, ("offer", "publication", "creation")) or "").strip(),
        )
        if fragment
    )
    if not empreinte_source:
        return ""

    digest = hashlib.sha1(empreinte_source.encode("utf-8")).hexdigest()
    return f"lba_{digest[:16]}"


def construire_localisation_lba(item: dict[str, Any]) -> str:
    """Construire une localisation lisible pour une offre LBA."""

    morceaux: list[str] = []

    for valeur in (
        lire_premiere_cle_profonde_lba(item, ("workplace", "location", "address")),
        lire_premiere_cle_profonde_lba(item, ("location", "address")),
        lire_premiere_cle_profonde_lba(item, ("location", "zip_code")),
        lire_premiere_cle_profonde_lba(item, ("location", "city")),
        lire_premiere_cle_profonde_lba(item, ("location", "label")),
    ):
        texte = str(valeur or "").strip()
        if texte and texte not in morceaux:
            morceaux.append(texte)

    return ", ".join(morceaux)


def est_opportunite_recruteur_lba(item: dict[str, Any]) -> bool:
    """Detecter les opportunites de type recruteur / candidature spontanee."""

    partner_label = str(
        lire_premiere_cle_profonde_lba(item, ("identifier", "partner_label")) or ""
    ).strip()
    if partner_label == "recruteurs_lba":
        return True

    # Sur les opportunites de type recruteur, le bloc `offer` est generalement
    # absent ou presque vide.
    titre = lire_premiere_cle_profonde_lba(item, ("offer", "title"))
    description = lire_premiere_cle_profonde_lba(item, ("offer", "description"))
    return not bool(str(titre or "").strip() or str(description or "").strip())


def mapper_offre_lba(raw_item: dict[str, Any]) -> dict[str, Any]:
    """Convertir une opportunite LBA vers le schema brut d'offre du projet."""

    partner_label = str(
        lire_premiere_cle_profonde_lba(raw_item, ("identifier", "partner_label")) or ""
    ).strip()
    company_name = str(
        lire_premiere_cle_profonde_lba(
            raw_item,
            ("workplace", "name"),
            ("workplace", "brand"),
            ("workplace", "legal_name"),
        )
        or ""
    ).strip()
    location_label = construire_localisation_lba(raw_item)
    contract_remote = convertir_valeur_lba_vers_texte(
        lire_premiere_cle_profonde_lba(raw_item, ("contract", "remote"))
    )
    application_url = convertir_valeur_lba_vers_texte(
        lire_premiere_cle_profonde_lba(raw_item, ("apply", "url"))
    )
    offer_url = convertir_valeur_lba_vers_texte(
        lire_premiere_cle_profonde_lba(raw_item, ("offer", "url"))
    )

    return {
        "source": "la_bonne_alternance",
        "external_id": construire_identifiant_lba(raw_item),
        "title": str(
            lire_premiere_cle_profonde_lba(raw_item, ("offer", "title")) or ""
        ).strip(),
        "company": company_name,
        "company_name": company_name,
        "location": location_label,
        "location_label": location_label,
        "salary": "",
        "salary_min": "",
        "salary_max": "",
        "contract_type": convertir_valeur_lba_vers_texte(
            lire_premiere_cle_profonde_lba(raw_item, ("contract", "type"))
        ),
        "published_at": convertir_valeur_lba_vers_texte(
            lire_premiere_cle_profonde_lba(raw_item, ("offer", "publication", "creation"))
        ),
        "application_deadline": convertir_valeur_lba_vers_texte(
            lire_premiere_cle_profonde_lba(raw_item, ("offer", "publication", "expiration"))
        ),
        "url": offer_url or application_url,
        "application_url": application_url,
        "description": str(
            lire_premiere_cle_profonde_lba(raw_item, ("offer", "description")) or ""
        ).strip(),
        "skills": construire_competences_lba(raw_item),
        "job_family": "alternance",
        "job_label": str(
            lire_premiere_cle_profonde_lba(raw_item, ("offer", "target_diploma"))
            or ""
        ).strip(),
        "job_code": ", ".join(
            str(code).strip()
            for code in (
                lire_premiere_cle_profonde_lba(raw_item, ("offer", "rome_codes")) or []
            )
            if str(code or "").strip()
        ),
        "public_sector": "",
        "category": partner_label,
        "telework": contract_remote,
        "partner_label": partner_label,
        "partner_job_id": str(
            lire_premiere_cle_profonde_lba(raw_item, ("identifier", "partner_job_id"))
            or ""
        ).strip(),
        "target_diploma": str(
            lire_premiere_cle_profonde_lba(raw_item, ("offer", "target_diploma"))
            or ""
        ).strip(),
        "opening_count": lire_premiere_cle_profonde_lba(raw_item, ("offer", "opening_count"))
        or 0,
        "contract_start": str(
            lire_premiere_cle_profonde_lba(raw_item, ("contract", "start")) or ""
        ).strip(),
        "contract_duration": str(
            lire_premiere_cle_profonde_lba(raw_item, ("contract", "duration")) or ""
        ).strip(),
        "workplace_siret": str(
            lire_premiere_cle_profonde_lba(raw_item, ("workplace", "siret")) or ""
        ).strip(),
        "workplace_website": str(
            lire_premiere_cle_profonde_lba(raw_item, ("workplace", "website")) or ""
        ).strip(),
        "apply_phone": str(
            lire_premiere_cle_profonde_lba(raw_item, ("apply", "phone")) or ""
        ).strip(),
        "apply_recipient_id": str(
            lire_premiere_cle_profonde_lba(raw_item, ("apply", "recipient_id")) or ""
        ).strip(),
        "raw_payload": raw_item,
    }


def collect_offres_la_bonne_alternance(
    api_key: str = "",
    export_endpoint: str = DEFAULT_LBA_EXPORT_ENDPOINT,
    timeout_seconds: int = DEFAULT_LBA_TIMEOUT_SECONDS,
    only_direct_offers: bool = DEFAULT_LBA_ONLY_DIRECT_OFFERS,
    enable_keyword_filter: bool = DEFAULT_LBA_ENABLE_KEYWORD_FILTER,
    include_recruiter_opportunities: bool = DEFAULT_LBA_INCLUDE_RECRUITER_OPPORTUNITIES,
) -> list[dict[str, Any]]:
    """Point d'entree principal pour la source La bonne alternance."""

    if not api_key.strip():
        print(
            "La bonne alternance: aucun jeton fourni. Renseigne `LBA_API_KEY` dans le `.env`."
        )
        return []

    try:
        download_url, last_update = demander_url_export_lba(
            api_key=api_key,
            export_endpoint=export_endpoint,
            timeout_seconds=timeout_seconds,
        )
        export_payload = telecharger_export_lba(
            download_url=download_url,
            timeout_seconds=timeout_seconds,
        )
    except (OSError, ValueError, requests.RequestException) as exc:
        print(f"La bonne alternance: echec de telechargement de l'export : {exc}")
        return []

    opportunites = extraire_opportunites_export_lba(export_payload)
    if not opportunites:
        print("La bonne alternance: aucune opportunite exploitable dans l'export JSON.")
        return []

    offres: list[dict[str, Any]] = []
    identifiants_vus: set[str] = set()
    compteur_recruteurs = 0
    compteur_hors_perimetre = 0
    compteur_partenaires = 0

    for opportunite in opportunites:
        if est_opportunite_recruteur_lba(opportunite):
            compteur_recruteurs += 1
            if not include_recruiter_opportunities:
                continue

        partner_label = str(
            lire_premiere_cle_profonde_lba(opportunite, ("identifier", "partner_label"))
            or ""
        ).strip()
        if only_direct_offers and partner_label != "offres_emploi_lba":
            compteur_partenaires += 1
            continue

        if enable_keyword_filter and not correspond_au_perimetre_data_lba(opportunite):
            compteur_hors_perimetre += 1
            continue

        offre = mapper_offre_lba(opportunite)
        external_id = str(offre.get("external_id") or "").strip()
        if not external_id or external_id in identifiants_vus:
            continue

        identifiants_vus.add(external_id)
        offres.append(offre)

    print(
        "La bonne alternance: "
        f"{len(offres)} offre(s) retenue(s) depuis {len(opportunites)} opportunite(s) "
        f"(maj export: {last_update or 'inconnue'})"
    )

    if not include_recruiter_opportunities:
        print(
            "La bonne alternance: "
            f"{compteur_recruteurs} opportunite(s) recruteur/candidature spontanee ignoree(s)."
        )

    if only_direct_offers:
        print(
            "La bonne alternance: "
            f"{compteur_partenaires} opportunite(s) partenaire ignoree(s) car "
            "`only_direct_offers` est actif."
        )

    if enable_keyword_filter:
        print(
            "La bonne alternance: "
            f"{compteur_hors_perimetre} opportunite(s) hors perimetre data/IA ignoree(s)."
        )

    return offres


def build_argument_parser() -> argparse.ArgumentParser:
    """Construire le parseur CLI du collecteur LBA."""

    parser = argparse.ArgumentParser(
        description="Collecte les offres La bonne alternance depuis l'export JSON officiel.",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Jeton d'acces LBA. Si vide, le script lira `LBA_API_KEY` dans l'environnement.",
    )
    parser.add_argument(
        "--only-direct-offers",
        action="store_true",
        help="Ne garder que les offres deposees directement sur La bonne alternance.",
    )
    parser.add_argument(
        "--include-recruiter-opportunities",
        action="store_true",
        help="Inclure aussi les opportunites de candidatures spontanees `recruteurs_lba`.",
    )
    parser.add_argument(
        "--disable-keyword-filter",
        action="store_true",
        help="Desactiver le filtrage metier data/IA/BI/cloud.",
    )
    return parser


def main() -> None:
    """Executer la collecte LBA depuis la ligne de commande."""

    charger_variables_environnement_locales()
    parser = build_argument_parser()
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("LBA_API_KEY", "")
    timeout_seconds = int(
        os.getenv("LBA_TIMEOUT_SECONDS", str(DEFAULT_LBA_TIMEOUT_SECONDS))
    )
    offres = collect_offres_la_bonne_alternance(
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        only_direct_offers=args.only_direct_offers
        or lire_booleen_lba(
            os.getenv("LBA_ONLY_DIRECT_OFFERS"),
            DEFAULT_LBA_ONLY_DIRECT_OFFERS,
        ),
        enable_keyword_filter=not args.disable_keyword_filter
        and lire_booleen_lba(
            os.getenv("LBA_ENABLE_KEYWORD_FILTER"),
            DEFAULT_LBA_ENABLE_KEYWORD_FILTER,
        ),
        include_recruiter_opportunities=args.include_recruiter_opportunities
        or lire_booleen_lba(
            os.getenv("LBA_INCLUDE_RECRUITER_OPPORTUNITIES"),
            DEFAULT_LBA_INCLUDE_RECRUITER_OPPORTUNITIES,
        ),
    )
    print(
        "La bonne alternance: "
        f"{len(offres)} offre(s) retournee(s) par le collecteur."
    )


if __name__ == "__main__":
    main()
