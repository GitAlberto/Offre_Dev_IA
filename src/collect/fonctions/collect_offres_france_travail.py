"""Module de collecte France Travail.

Ce fichier est le premier connecteur de source qui realise maintenant un vrai
travail au lieu de rester un simple placeholder.

Ce module a pour responsabilites :
- s'authentifier aupres de l'endpoint OAuth France Travail ;
- construire les parametres de recherche pour l'endpoint des offres ;
- appeler l'API des offres ;
- mapper chaque ligne distante vers le schema brut du projet ;
- utiliser si besoin un fichier local de secours si l'API n'est pas disponible.

Ce qui est cense appeler ce module :
- `src/collect/collect.py` doit appeler `collect_offres_france_travail()` ;
- `src/pipeline.py` devra plus tard passer par l'orchestrateur plutot que
  d'importer ce module directement dans le flux normal ;
- les developpeurs peuvent tout de meme appeler ce fichier isole pour valider la source.

Ce que ce module est cense appeler en interne :
- l'endpoint de token France Travail ;
- l'endpoint de recherche d'offres France Travail ;
- des helpers locaux qui construisent les parametres, chargent les secours et mappent les lignes.

Limite importante :
- ce fichier ne collecte et ne mappe que la source France Travail ;
- le nettoyage, la normalisation et la deduplication globaux restent du ressort
  de `src/transform/nettoyage/` ;
- le dataset final fusionne reste du ressort de
  `src/transform/aggregate/aggregate.py`.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRANCE_TRAVAIL_TOKEN_URL = (
    "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
    "?realm=/partenaire"
)
FRANCE_TRAVAIL_SEARCH_URL = (
    "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
)
DEFAULT_FRANCE_TRAVAIL_TIMEOUT_SECONDS = 30
DEFAULT_FRANCE_TRAVAIL_MAX_RESULTS = 150
DEFAULT_FRANCE_TRAVAIL_MAX_PAGES = 20
DEFAULT_FRANCE_TRAVAIL_QUERY_MODE = "broad"
DEFAULT_FRANCE_TRAVAIL_FALLBACK_PATH = (
    PROJECT_ROOT / "data" / "fallback" / "fallback_france_travail.json"
)
FRANCE_TRAVAIL_ALTERNANCE_CONTRACT_CODE = "E1"
FRANCE_TRAVAIL_KEYWORD_GROUPS_BY_MODE: dict[str, list[list[str]]] = {
    "legacy": [
        ["intelligence artificielle", "data engineer"],
    ],
    "focused": [
        ["data engineer"],
        ["data scientist"],
        ["machine learning"],
        ["intelligence artificielle"],
        ["artificial intelligence"],
        ["data analyst"],
        ["business intelligence"],
        ["big data"],
        ["mlops"],
        ["computer vision"],
        ["deep learning"],
    ],
    "broad": [
        ["data"],
        ["data engineer"],
        ["data scientist"],
        ["data analyst"],
        ["machine learning"],
        ["intelligence artificielle"],
        ["artificial intelligence"],
        ["business intelligence"],
        ["big data"],
        ["mlops"],
        ["computer vision"],
        ["deep learning"],
    ],
    "max_volume": [
        ["data"],
        ["data engineer"],
        ["data scientist"],
        ["data analyst"],
        ["machine learning"],
        ["intelligence artificielle"],
        ["business intelligence"],
        ["big data"],
        ["mlops"],
        ["computer vision"],
        ["deep learning"],
        ["python"],
        ["sql"],
        ["tableau"],
        ["power bi"],
        ["analytics"],
        ["llm"],
    ],
}
FRANCE_TRAVAIL_DATA_ENGINEERING_TERMS = [
    "data engineer",
    "ing\u00e9nieur donn\u00e9es",
    "ing\u00e9nieur data",
    "data pipeline",
    "ETL d\u00e9veloppeur",
    "d\u00e9veloppeur ETL",
    "ing\u00e9nieur ETL",
    "data integration",
    "int\u00e9gration donn\u00e9es",
    "DataOps",
]
FRANCE_TRAVAIL_IA_ML_TERMS = [
    "d\u00e9veloppeur intelligence artificielle",
    "d\u00e9veloppeur IA",
    "machine learning engineer",
    "ing\u00e9nieur machine learning",
    "ML engineer",
    "MLOps",
    "MLOps engineer",
    "ing\u00e9nieur MLOps",
    "deep learning",
    "NLP engineer",
    "computer vision engineer",
    "ing\u00e9nieur NLP",
    "LLM engineer",
    "AI engineer",
]
FRANCE_TRAVAIL_DATA_SCIENCE_TERMS = [
    "data scientist",
    "analyste donn\u00e9es",
    "analyste data",
    "data analyst",
    "business analyst data",
    "statisticien donn\u00e9es",
    "scientist donn\u00e9es",
    "analyste d\u00e9cisionnel",
    "analyste BI",
    "business intelligence",
]
FRANCE_TRAVAIL_ARCHITECTURE_CLOUD_TERMS = [
    "architecte data",
    "data architect",
    "cloud data engineer",
    "ing\u00e9nieur cloud donn\u00e9es",
    "architecte cloud",
    "data platform engineer",
    "ing\u00e9nieur plateforme donn\u00e9es",
    "AWS data",
    "Azure data",
    "GCP data",
    "Databricks",
    "Snowflake",
]
FRANCE_TRAVAIL_ALTERNANCE_TERMS = [
    "alternance data",
    "apprentissage data",
    "alternance IA",
    "alternance machine learning",
    "alternance data engineer",
]
FRANCE_TRAVAIL_STAGE_TERMS = [
    "stage data",
    "stage IA",
]
FRANCE_TRAVAIL_TITRES_FR_TERMS = [
    "chef de projet data",
    "responsable data",
    "lead data",
    "consultant data",
    "consultant BI",
    "consultant d\u00e9cisionnel",
    "d\u00e9veloppeur Python data",
    "d\u00e9veloppeur Python IA",
    "ing\u00e9nieur analytique",
    "ing\u00e9nieur d\u00e9cisionnel",
    "d\u00e9veloppeur big data",
    "ing\u00e9nieur big data",
    "Spark engineer",
    "ing\u00e9nieur Spark",
    "Kafka engineer",
    "Airflow",
    "dbt developer",
    "d\u00e9veloppeur dbt",
]
FRANCE_TRAVAIL_OUTILS_TERMS = [
    "Apache Spark",
    "Apache Kafka",
    "Apache Airflow",
    "dbt",
    "Apache NiFi",
    "Elasticsearch data",
    "Power BI d\u00e9veloppeur",
    "Tableau d\u00e9veloppeur",
    "Looker",
    "Grafana data",
]


def request_france_travail_access_token(
    client_id: str,
    client_secret: str,
    timeout_seconds: int = DEFAULT_FRANCE_TRAVAIL_TIMEOUT_SECONDS,
    scope: str = "",
) -> str:
    """Demander un token OAuth d'acces a France Travail.

    Appelant attendu :
    - `collect_offres_france_travail()`.

    Pourquoi ce helper est volontairement isole :
    - l'authentification est une preoccupation technique distincte ;
    - cela garde le collecteur principal plus lisible ;
    - cela fournit un point unique pour faire evoluer le flux d'auth plus tard
      si l'API partenaire change.

    Comportement actuel :
    - retourne une chaine contenant le token d'acces quand l'authentification reussit ;
    - retourne une chaine vide si les identifiants manquent ou si l'appel echoue.
    """

    if not client_id or not client_secret:
        print(
            "France Travail: identifiants manquants, demande de token OAuth ignoree."
        )
        return ""

    if not scope:
        print(
            "France Travail: scope manquant. Une erreur 400 sur le token est "
            "souvent causee par un scope vide. Exemple pour l'API des offres : "
            "'api_offresdemploiv2 o2dsoffre'."
        )

    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    if scope:
        payload["scope"] = scope

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        response = requests.post(
            FRANCE_TRAVAIL_TOKEN_URL,
            data=payload,
            headers=headers,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        response_payload = response.json()
    except requests.HTTPError as exc:
        error_body = ""
        if exc.response is not None:
            try:
                error_body = exc.response.text.strip()
            except Exception:
                error_body = ""

        if error_body:
            print(
                "France Travail: echec de la demande de token OAuth avec HTTP "
                f"{exc.response.status_code}: {error_body[:500]}"
            )
        else:
            print(f"France Travail: echec de la demande de token OAuth : {exc}")
        return ""
    except requests.RequestException as exc:
        print(f"France Travail: echec de la demande de token OAuth : {exc}")
        return ""
    except ValueError as exc:
        print(f"France Travail: la reponse OAuth n'est pas un JSON valide : {exc}")
        return ""

    access_token = response_payload.get("access_token", "")
    return str(access_token) if access_token else ""


def build_france_travail_search_params(
    keywords: list[str] | None = None,
    contract_code: str | None = None,
    departement: str | None = None,
) -> dict[str, Any]:
    """Construire les parametres de requete pour l'endpoint de recherche des offres.

    Appelant attendu :
    - `collect_offres_france_travail()`.

    Objectif :
    - separer la logique de construction de requete de l'appel HTTP ;
    - rendre les filtres choisis explicites ;
    - eviter de melanger la logique de filtrage et la logique de transport dans le meme bloc.
    """

    params = {
        "motsCles": " OR ".join(
            keywords or ["intelligence artificielle", "data engineer"]
        ),
        "typeContrat": contract_code,
        "departement": departement,
    }

    return {
        key: value
        for key, value in params.items()
        if value not in (None, "")
    }


def build_france_travail_search_headers(
    access_token: str,
) -> dict[str, str]:
    """Construire les en-tetes HTTP pour l'appel de recherche d'offres.

    Appelant attendu :
    - `fetch_france_travail_offers_page()`.

    Note importante :
    - la pagination est pilotee par le parametre de requete `range` ;
    - les en-tetes ne portent ici que l'authentification et la negociation de contenu.
    """

    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }


def build_france_travail_range_value(
    range_start: int = 0,
    max_results: int = DEFAULT_FRANCE_TRAVAIL_MAX_RESULTS,
) -> str:
    """Construire le parametre de requete `range` attendu par l'API des offres."""

    safe_range_start = max(0, range_start)
    safe_max_results = max(1, min(max_results, DEFAULT_FRANCE_TRAVAIL_MAX_RESULTS))
    range_end = safe_range_start + safe_max_results - 1
    return f"{safe_range_start}-{range_end}"


def parse_france_travail_content_range(
    content_range: str | None,
) -> tuple[int | None, int | None, int | None]:
    """Analyser un en-tete `Content-Range` retourne par France Travail.

    Formats observes sur l'API live :
    - `offres 0-149/454`
    - `*/0`
    """

    if not content_range:
        return (None, None, None)

    empty_match = re.search(r"\*/(\d+)$", content_range)
    if empty_match:
        return (None, None, int(empty_match.group(1)))

    match = re.search(r"(\d+)-(\d+)/(\d+)$", content_range)
    if not match:
        return (None, None, None)

    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
    )


def fetch_france_travail_offers_page(
    access_token: str,
    params: dict[str, Any],
    range_start: int = 0,
    max_results: int = DEFAULT_FRANCE_TRAVAIL_MAX_RESULTS,
    timeout_seconds: int = DEFAULT_FRANCE_TRAVAIL_TIMEOUT_SECONDS,
) -> tuple[list[dict[str, Any]], str, int | None]:
    """Recuperer une page paginee depuis l'endpoint des offres France Travail.

    Appelant attendu :
    - `fetch_all_france_travail_offers_for_query()`.

    Comportement actuel :
    - retourne les lignes d'une page unique ainsi que la valeur de l'en-tete `Content-Range` ;
    - retourne une liste vide si l'appel HTTP echoue ou si la charge utile est inutilisable.
    """

    if not access_token:
        return ([], "", None)

    headers = build_france_travail_search_headers(
        access_token=access_token,
    )
    request_params = dict(params)
    request_params["range"] = build_france_travail_range_value(
        range_start=range_start,
        max_results=max_results,
    )

    try:
        response = requests.get(
            FRANCE_TRAVAIL_SEARCH_URL,
            headers=headers,
            params=request_params,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        print(f"France Travail: echec de la requete d'offres : {exc}")
        return ([], "", status_code)
    except requests.RequestException as exc:
        print(f"France Travail: echec de la requete d'offres : {exc}")
        return ([], "", None)

    content_range = response.headers.get("Content-Range", "")

    if response.status_code == 204 or not response.content:
        return ([], content_range, None)

    try:
        response_payload = response.json()
    except ValueError as exc:
        print(f"France Travail: la reponse des offres n'est pas un JSON valide : {exc}")
        return ([], content_range, None)

    if isinstance(response_payload, dict):
        result_rows = (
            response_payload.get("resultats")
            or response_payload.get("results")
            or response_payload.get("items")
            or []
        )
    elif isinstance(response_payload, list):
        result_rows = response_payload
    else:
        result_rows = []

    return ([row for row in result_rows if isinstance(row, dict)], content_range, None)


def build_france_travail_query_spec(
    keywords: list[str],
    contract_code: str | None = None,
    departement: str | None = None,
) -> dict[str, Any]:
    """Construire une specification de requete normalisee pour l'API des offres."""

    cleaned_keywords = [
        keyword.strip()
        for keyword in keywords
        if isinstance(keyword, str) and keyword.strip()
    ]

    query_spec: dict[str, Any] = {"keywords": cleaned_keywords}

    if contract_code not in (None, ""):
        query_spec["contract_code"] = contract_code

    if departement not in (None, ""):
        query_spec["departement"] = departement

    return query_spec


def build_france_travail_query_specs_from_keyword_groups(
    keyword_groups: list[list[str]],
) -> list[dict[str, Any]]:
    """Convertir des groupes de mots-cles bruts en specifications de requete normalisees."""

    query_specs: list[dict[str, Any]] = []

    for keyword_group in keyword_groups:
        query_spec = build_france_travail_query_spec(keyword_group)
        if query_spec["keywords"]:
            query_specs.append(query_spec)

    return query_specs


def build_france_travail_query_specs_from_terms(
    terms: list[str],
    contract_code: str | None = None,
) -> list[dict[str, Any]]:
    """Construire une specification de requete par terme de recherche.

    Ce choix est volontairement different du constructeur par groupes :
    - France Travail gere parfois mieux des requetes simples que de longues chaines `OR` ;
    - les requetes individuelles augmentent le rappel et restent plus faciles a debugger ;
    - la deduplication en aval absorbe le chevauchement attendu.
    """

    query_specs: list[dict[str, Any]] = []

    for term in terms:
        query_spec = build_france_travail_query_spec(
            keywords=[term],
            contract_code=contract_code,
        )
        if query_spec["keywords"]:
            query_specs.append(query_spec)

    return query_specs


def build_france_travail_max_volume_query_specs() -> list[dict[str, Any]]:
    """Construire le preset le plus large utilise pour maximiser le volume France Travail.

    Strategie retenue ici :
    - conserver les requetes larges deja performantes ;
    - ajouter les familles de mots-cles metier en francais fournies pendant le tuning ;
    - ajouter une passe dediee a l'alternance avec tentative de filtre `typeContrat=E1` ;
    - conserver une petite passe orientee stages sans imposer de type de contrat.
    """

    query_specs = [
        build_france_travail_query_spec(["data"]),
        build_france_travail_query_spec(["machine learning"]),
        build_france_travail_query_spec(["intelligence artificielle"]),
        build_france_travail_query_spec(["big data"]),
        build_france_travail_query_spec(["computer vision"]),
        build_france_travail_query_spec(["python"]),
        build_france_travail_query_spec(["sql"]),
        build_france_travail_query_spec(["tableau"]),
        build_france_travail_query_spec(["power bi"]),
        build_france_travail_query_spec(["analytics"]),
        build_france_travail_query_spec(["llm"]),
    ]

    query_specs.extend(
        build_france_travail_query_specs_from_terms(FRANCE_TRAVAIL_DATA_ENGINEERING_TERMS)
    )
    query_specs.extend(
        build_france_travail_query_specs_from_terms(FRANCE_TRAVAIL_IA_ML_TERMS)
    )
    query_specs.extend(
        build_france_travail_query_specs_from_terms(FRANCE_TRAVAIL_DATA_SCIENCE_TERMS)
    )
    query_specs.extend(
        build_france_travail_query_specs_from_terms(
            FRANCE_TRAVAIL_ARCHITECTURE_CLOUD_TERMS
        )
    )
    query_specs.extend(
        build_france_travail_query_specs_from_terms(FRANCE_TRAVAIL_TITRES_FR_TERMS)
    )
    query_specs.extend(
        build_france_travail_query_specs_from_terms(FRANCE_TRAVAIL_OUTILS_TERMS)
    )
    query_specs.extend(
        build_france_travail_query_specs_from_terms(
            FRANCE_TRAVAIL_ALTERNANCE_TERMS,
            contract_code=FRANCE_TRAVAIL_ALTERNANCE_CONTRACT_CODE,
        )
    )
    query_specs.extend(
        build_france_travail_query_specs_from_terms(FRANCE_TRAVAIL_STAGE_TERMS)
    )

    return [query_spec for query_spec in query_specs if query_spec["keywords"]]


def resolve_france_travail_query_specs(
    keywords: list[str] | None = None,
    keyword_groups: list[list[str]] | None = None,
    query_mode: str = DEFAULT_FRANCE_TRAVAIL_QUERY_MODE,
) -> list[dict[str, Any]]:
    """Resolve which query specifications should be executed."""

    if keyword_groups:
        query_specs = build_france_travail_query_specs_from_keyword_groups(
            keyword_groups
        )
        if query_specs:
            return query_specs

    if keywords:
        query_specs = build_france_travail_query_specs_from_keyword_groups([keywords])
        if query_specs:
            return query_specs

    normalized_query_mode = query_mode.strip().lower()
    known_query_modes = set(FRANCE_TRAVAIL_KEYWORD_GROUPS_BY_MODE) | {"max_volume"}
    if normalized_query_mode not in known_query_modes:
        print(
            "France Travail: mode de requete inconnu "
            f"'{query_mode}', repli sur '{DEFAULT_FRANCE_TRAVAIL_QUERY_MODE}'."
        )
        normalized_query_mode = DEFAULT_FRANCE_TRAVAIL_QUERY_MODE

    if normalized_query_mode == "max_volume":
        return build_france_travail_max_volume_query_specs()

    return build_france_travail_query_specs_from_keyword_groups(
        FRANCE_TRAVAIL_KEYWORD_GROUPS_BY_MODE[normalized_query_mode]
    )


def build_france_travail_raw_offer_dedup_key(
    raw_offer: dict[str, Any],
) -> tuple[str, ...]:
    """Construire une cle de deduplication stable pour une offre France Travail brute."""

    external_id = raw_offer.get("id")
    if external_id:
        return ("id", str(external_id))

    company_block = raw_offer.get("entreprise")
    location_block = raw_offer.get("lieuTravail")
    company_details = company_block if isinstance(company_block, dict) else {}
    location_details = location_block if isinstance(location_block, dict) else {}

    return (
        "secours",
        str(raw_offer.get("intitule") or ""),
        str(company_details.get("nom") or ""),
        str(
            location_details.get("libelle")
            or location_details.get("commune")
            or location_details.get("codePostal")
            or ""
        ),
        str(
            raw_offer.get("dateCreation")
            or raw_offer.get("dateActualisation")
            or ""
        ),
    )


def deduplicate_france_travail_raw_offers(
    raw_offers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Dedoublonner les lignes France Travail brutes collectees via plusieurs requetes."""

    seen_keys: set[tuple[str, ...]] = set()
    deduplicated_rows: list[dict[str, Any]] = []

    for raw_offer in raw_offers:
        dedup_key = build_france_travail_raw_offer_dedup_key(raw_offer)
        if dedup_key in seen_keys:
            continue

        seen_keys.add(dedup_key)
        deduplicated_rows.append(raw_offer)

    return deduplicated_rows


def fetch_all_france_travail_offers_for_query(
    access_token: str,
    keywords: list[str],
    contract_code: str | None = None,
    departement: str | None = None,
    max_results: int = DEFAULT_FRANCE_TRAVAIL_MAX_RESULTS,
    timeout_seconds: int = DEFAULT_FRANCE_TRAVAIL_TIMEOUT_SECONDS,
    max_pages: int | None = DEFAULT_FRANCE_TRAVAIL_MAX_PAGES,
) -> list[dict[str, Any]]:
    """Collecter toutes les pages pour un jeu de mots-cles France Travail."""

    params = build_france_travail_search_params(
        keywords=keywords,
        contract_code=contract_code,
        departement=departement,
    )
    safe_page_size = max(1, min(max_results, DEFAULT_FRANCE_TRAVAIL_MAX_RESULTS))
    query_label = " OR ".join(keywords)
    if contract_code:
        query_label = f"{query_label} [typeContrat={contract_code}]"

    collected_rows: list[dict[str, Any]] = []
    page_index = 0

    while True:
        current_range_start = page_index * safe_page_size
        page_rows, content_range, error_status_code = fetch_france_travail_offers_page(
            access_token=access_token,
            params=params,
            range_start=current_range_start,
            max_results=safe_page_size,
            timeout_seconds=timeout_seconds,
        )

        if (
            page_index == 0
            and contract_code
            and error_status_code == 400
        ):
            print(
                "France Travail: "
                f"filtre de contrat '{contract_code}' refuse pour la requete '{query_label}'. "
                "Nouvelle tentative avec les memes mots-cles sans filtre de contrat."
            )
            return fetch_all_france_travail_offers_for_query(
                access_token=access_token,
                keywords=keywords,
                contract_code=None,
                departement=departement,
                max_results=max_results,
                timeout_seconds=timeout_seconds,
                max_pages=max_pages,
            )

        _, response_range_end, total_available = parse_france_travail_content_range(
            content_range
        )

        print(
            "France Travail: "
            f"requete='{query_label}' "
            f"page={page_index + 1} "
            f"range='{build_france_travail_range_value(current_range_start, safe_page_size)}' "
            f"lignes={len(page_rows)} "
            f"content_range='{content_range or 'n/a'}'"
        )

        if not page_rows:
            break

        collected_rows.extend(page_rows)

        if total_available is not None and response_range_end is not None:
            if response_range_end >= total_available - 1:
                break

        if len(page_rows) < safe_page_size:
            break

        if max_pages is not None and page_index + 1 >= max_pages:
            print(
                "France Travail: "
                f"requete='{query_label}' arretee apres {max_pages} page(s)."
            )
            break

        page_index += 1

    return collected_rows


def extract_france_travail_salary(raw_offer: dict[str, Any]) -> str | None:
    """Extraire un libelle de salaire lisible depuis la charge utile France Travail."""

    salary_block = raw_offer.get("salaire")

    if isinstance(salary_block, dict):
        return (
            salary_block.get("libelle")
            or salary_block.get("commentaire")
            or salary_block.get("complement1")
            or salary_block.get("complement2")
        )

    if isinstance(salary_block, str):
        return salary_block

    return None


def extract_france_travail_skills(raw_offer: dict[str, Any]) -> list[str]:
    """Extraire les competences d'une offre France Travail quand elles sont presentes.

    La forme exacte de l'API peut varier, donc ce helper reste volontairement defensif.
    """

    skills: list[str] = []
    raw_skills = raw_offer.get("competences") or []

    if not isinstance(raw_skills, list):
        return skills

    for raw_skill in raw_skills:
        if isinstance(raw_skill, dict):
            label = raw_skill.get("libelle") or raw_skill.get("code")
        else:
            label = str(raw_skill)

        if label:
            skills.append(str(label))

    return skills


def map_france_travail_offer(raw_offer: dict[str, Any]) -> dict[str, Any]:
    """Convertir une offre France Travail vers le schema brut du projet.

    Appelant attendu :
    - `collect_offres_france_travail()` une fois la reponse HTTP lue.

    Ce mapping reste volontairement oriente source :
    - il preserve la charge utile brute pour le debug ;
    - il expose quelques champs de premier niveau utiles pour la suite ;
    - il laisse tout de meme la normalisation complete a la couche de nettoyage aval.
    """

    company_block = raw_offer.get("entreprise")
    location_block = raw_offer.get("lieuTravail")

    company_details = company_block if isinstance(company_block, dict) else {}
    location_details = location_block if isinstance(location_block, dict) else {}

    return {
        "source": "france_travail",
        "external_id": raw_offer.get("id"),
        "title": raw_offer.get("intitule"),
        "company": company_details,
        "company_name": company_details.get("nom"),
        "location": location_details,
        "location_label": (
            location_details.get("libelle")
            or location_details.get("commune")
            or location_details.get("codePostal")
        ),
        "salary": extract_france_travail_salary(raw_offer),
        "contract_type": (
            raw_offer.get("typeContratLibelle")
            or raw_offer.get("typeContrat")
        ),
        "published_at": (
            raw_offer.get("dateCreation")
            or raw_offer.get("dateActualisation")
        ),
        "description": raw_offer.get("description"),
        "skills": extract_france_travail_skills(raw_offer),
        "raw_payload": raw_offer,
    }


def load_france_travail_fallback(
    fallback_path: Path = DEFAULT_FRANCE_TRAVAIL_FALLBACK_PATH,
) -> list[dict[str, Any]]:
    """Charger un jeu de donnees local de secours pour une execution hors ligne ou de demonstration.

    Appelant attendu :
    - `collect_offres_france_travail()` quand le mode demonstration est actif
      ou quand l'API live est temporairement indisponible.

    Formats acceptes :
    - liste JSON de lignes deja mappees ;
    - dictionnaire JSON contenant une liste `resultats` issue de France Travail ;
    - fichier CSV contenant soit des lignes deja mappees, soit des colonnes brutes simplifiees.
    """

    if not fallback_path.exists():
        return []

    if fallback_path.suffix.lower() == ".json":
        try:
            with fallback_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, ValueError) as exc:
            print(f"France Travail: impossible de lire le secours JSON : {exc}")
            return []

        if isinstance(payload, list):
            rows = [row for row in payload if isinstance(row, dict)]
        elif isinstance(payload, dict):
            result_rows = payload.get("resultats", [])
            rows = [row for row in result_rows if isinstance(row, dict)]
        else:
            rows = []

        if rows and "source" in rows[0]:
            return rows

        return [map_france_travail_offer(row) for row in rows]

    if fallback_path.suffix.lower() == ".csv":
        try:
            with fallback_path.open("r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                rows = [dict(row) for row in reader]
        except OSError as exc:
            print(f"France Travail: impossible de lire le secours CSV : {exc}")
            return []

        if rows and "source" in rows[0]:
            return rows

        return [
            {
                "source": "france_travail",
                "external_id": row.get("external_id") or row.get("id"),
                "title": row.get("title") or row.get("intitule"),
                "company": {},
                "company_name": row.get("company_name") or row.get("entreprise"),
                "location": {},
                "location_label": row.get("location_label")
                or row.get("location")
                or row.get("lieu"),
                "salary": row.get("salary") or row.get("salaire"),
                "contract_type": row.get("contract_type")
                or row.get("type_contrat"),
                "published_at": row.get("published_at")
                or row.get("date_publication"),
                "description": row.get("description"),
                "skills": [],
                "raw_payload": row,
            }
            for row in rows
        ]

    print(
        "France Travail: format de secours non supporte, formats attendus : .json ou .csv."
    )
    return []


def collect_offres_france_travail(
    client_id: str = "",
    client_secret: str = "",
    keywords: list[str] | None = None,
    keyword_groups: list[list[str]] | None = None,
    contract_code: str | None = None,
    departement: str | None = None,
    max_results: int = DEFAULT_FRANCE_TRAVAIL_MAX_RESULTS,
    max_pages: int | None = DEFAULT_FRANCE_TRAVAIL_MAX_PAGES,
    timeout_seconds: int = DEFAULT_FRANCE_TRAVAIL_TIMEOUT_SECONDS,
    scope: str = "",
    query_mode: str = DEFAULT_FRANCE_TRAVAIL_QUERY_MODE,
    use_fallback_if_unavailable: bool = False,
    fallback_path: Path = DEFAULT_FRANCE_TRAVAIL_FALLBACK_PATH,
) -> list[dict[str, Any]]:
    """Point d'entree principal pour la collecte des offres France Travail.

    Appelant attendu :
    - `src/collect/collect.py` pendant la phase de collecte multi-sources.

    Ordre d'execution interne :
    1. obtenir un token OAuth avec `request_france_travail_access_token()`
    2. resoudre une ou plusieurs specifications de requete pour mieux couvrir le domaine cible
    3. paginer chaque requete avec `fetch_all_france_travail_offers_for_query()`
    4. dedoublonner les lignes brutes issues de recherches qui se recouvrent
    5. mapper chaque offre brute avec `map_france_travail_offer()`
    6. utiliser si besoin un fichier local de secours si le chemin live est indisponible

    Sortie :
    - une liste de dictionnaires d'offres encore bruts mais structures ;
    - un dictionnaire par offre collectee ;
    - toujours pas totalement normalisee pour la couche base de donnees.
    """
    query_specs = resolve_france_travail_query_specs(
        keywords=keywords,
        keyword_groups=keyword_groups,
        query_mode=query_mode,
    )

    token = request_france_travail_access_token(
        client_id=client_id,
        client_secret=client_secret,
        timeout_seconds=timeout_seconds,
        scope=scope,
    )

    if not token:
        if use_fallback_if_unavailable:
            fallback_rows = load_france_travail_fallback(fallback_path=fallback_path)
            if fallback_rows:
                print(
                    "France Travail: utilisation du secours local car aucun token "
                    "live n'a pu etre obtenu."
                )
            return fallback_rows
        return []

    raw_offers: list[dict[str, Any]] = []

    for query_spec in query_specs:
        raw_offers.extend(
            fetch_all_france_travail_offers_for_query(
                access_token=token,
                keywords=query_spec.get("keywords", []),
                contract_code=(
                    contract_code
                    if contract_code is not None
                    else query_spec.get("contract_code")
                ),
                departement=(
                    departement
                    if departement is not None
                    else query_spec.get("departement")
                ),
                max_results=max_results,
                max_pages=max_pages,
                timeout_seconds=timeout_seconds,
            )
        )

    if not raw_offers and use_fallback_if_unavailable:
        fallback_rows = load_france_travail_fallback(fallback_path=fallback_path)
        if fallback_rows:
            print(
                "France Travail: utilisation du secours local car la requete "
                "live des offres n'a renvoye aucune ligne exploitable."
            )
        return fallback_rows

    deduplicated_raw_offers = deduplicate_france_travail_raw_offers(raw_offers)
    print(
        "France Travail: "
        f"{len(deduplicated_raw_offers)} offre(s) unique(s) conservee(s) apres deduplication "
        f"a partir de {len(raw_offers)} ligne(s) brute(s) sur {len(query_specs)} specification(s) de requete."
    )

    return [
        map_france_travail_offer(raw_offer)
        for raw_offer in deduplicated_raw_offers
    ]
