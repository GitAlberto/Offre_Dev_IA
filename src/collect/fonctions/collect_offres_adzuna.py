"""Collecteur isole des offres Adzuna.

Objectif :
- alimenter la simulation PostgreSQL avec une source salary-friendly ;
- garder Adzuna hors de l'orchestrateur principal pour ne pas melanger la
  source base de donnees avec les sources live du pipeline ;
- verifier la presence effective de salaires structures avant chargement SQL.

References officielles :
- overview : https://developer.adzuna.com/overview
- search ads : https://developer.adzuna.com/docs/search
- documentation interactive : https://developer.adzuna.com/activedocs
- terms : https://developer.adzuna.com/docs/terms_of_service
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - repli simple si la dependance manque
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ADZUNA_API_ROOT = "https://api.adzuna.com/v1/api/jobs"
DEFAULT_ADZUNA_COUNTRY = "fr"
DEFAULT_ADZUNA_RESULTS_PER_PAGE = 50
DEFAULT_ADZUNA_MAX_PAGES = 3
DEFAULT_ADZUNA_TIMEOUT_SECONDS = 60
DEFAULT_ADZUNA_QUERY_MODE = "focused"
DEFAULT_ADZUNA_REQUIRE_SALARY = True
DEFAULT_ADZUNA_EXCLUDE_PREDICTED_SALARY = False

ADZUNA_QUERY_GROUPS = {
    "focused": [
        "data engineer",
        "data scientist",
        "data analyst",
        "machine learning engineer",
        "mlops engineer",
        "ai engineer",
        "analytics engineer",
    ],
    "broad": [
        "data engineer",
        "data scientist",
        "data analyst",
        "machine learning engineer",
        "mlops engineer",
        "ai engineer",
        "analytics engineer",
        "business intelligence",
        "data architect",
        "cloud data engineer",
        "power bi",
        "tableau",
        "python data",
        "sql data",
    ],
}


def charger_variables_environnement_locales() -> None:
    """Charger `.env` si `python-dotenv` est disponible."""

    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")


def lire_booleen_adzuna(raw_value: Any, default: bool) -> bool:
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


def construire_url_page_adzuna(
    country: str,
    page_number: int,
    api_root: str = DEFAULT_ADZUNA_API_ROOT,
) -> str:
    """Construire l'URL d'une page de recherche Adzuna."""

    return f"{api_root}/{country}/search/{page_number}"


def construire_params_recherche_adzuna(
    app_id: str,
    app_key: str,
    query: str,
    results_per_page: int,
) -> dict[str, Any]:
    """Construire les parametres HTTP de recherche Adzuna."""

    return {
        "app_id": app_id,
        "app_key": app_key,
        "what": query,
        "results_per_page": max(1, min(results_per_page, 50)),
        "content-type": "application/json",
    }


def telecharger_page_adzuna(
    app_id: str,
    app_key: str,
    query: str,
    country: str,
    page_number: int,
    results_per_page: int,
    timeout_seconds: int,
    api_root: str = DEFAULT_ADZUNA_API_ROOT,
) -> tuple[list[dict[str, Any]], int | None]:
    """Telecharger une page de resultats Adzuna."""

    response = requests.get(
        construire_url_page_adzuna(
            country=country,
            page_number=page_number,
            api_root=api_root,
        ),
        params=construire_params_recherche_adzuna(
            app_id=app_id,
            app_key=app_key,
            query=query,
            results_per_page=results_per_page,
        ),
        headers={"Accept": "application/json", "User-Agent": "JobRadar-IA/1.0"},
        timeout=timeout_seconds,
    )
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict):
        return [], None

    resultats = payload.get("results", [])
    if not isinstance(resultats, list):
        resultats = []

    total_count = payload.get("count")
    if not isinstance(total_count, int):
        total_count = None

    return [item for item in resultats if isinstance(item, dict)], total_count


def construire_horodatage_adzuna() -> str:
    """Retourner un horodatage de fichier stable."""

    return datetime.now().strftime("%Y%m%d_%H%M%S")


def sauvegarder_collecte_brute_adzuna(
    offres: list[dict[str, Any]],
    output_directory: Path = PROJECT_ROOT / "data" / "raw",
) -> Path:
    """Sauvegarder la collecte Adzuna dans un JSON brut dedie."""

    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / f"adzuna_{construire_horodatage_adzuna()}.json"
    payload = {"adzuna": offres}
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2, default=str)
    return output_path


def construire_salaire_adzuna(raw_row: dict[str, Any]) -> str:
    """Construire un texte de salaire lisible."""

    salaire_min = raw_row.get("salary_min")
    salaire_max = raw_row.get("salary_max")

    if salaire_min and salaire_max:
        return f"{salaire_min} - {salaire_max}"
    if salaire_min:
        return str(salaire_min)
    if salaire_max:
        return str(salaire_max)
    return ""


def a_un_salaire_adzuna(raw_row: dict[str, Any]) -> bool:
    """Verifier si une annonce Adzuna expose au moins une borne de salaire."""

    return bool(raw_row.get("salary_min") or raw_row.get("salary_max"))


def est_salaire_predit_adzuna(raw_row: dict[str, Any]) -> bool:
    """Verifier si le salaire est marque comme predit par Adzuna."""

    return bool(raw_row.get("salary_is_predicted"))


def mapper_offre_adzuna(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Convertir une annonce Adzuna vers le schema brut d'offre du projet."""

    company_name = str(
        (raw_row.get("company") or {}).get("display_name") or ""
    ).strip()
    location_label = str(
        (raw_row.get("location") or {}).get("display_name") or ""
    ).strip()
    category = raw_row.get("category") or {}

    return {
        "source": "adzuna",
        "external_id": str(raw_row.get("id") or "").strip(),
        "title": str(raw_row.get("title") or "").strip(),
        "company": company_name,
        "company_name": company_name,
        "location": location_label,
        "location_label": location_label,
        "salary": construire_salaire_adzuna(raw_row),
        "salary_min": raw_row.get("salary_min") or "",
        "salary_max": raw_row.get("salary_max") or "",
        "salary_is_predicted": 1 if est_salaire_predit_adzuna(raw_row) else 0,
        "contract_type": str(raw_row.get("contract_type") or "").strip(),
        "contract_time": str(raw_row.get("contract_time") or "").strip(),
        "published_at": str(raw_row.get("created") or "").strip(),
        "application_deadline": "",
        "url": str(raw_row.get("redirect_url") or "").strip(),
        "application_url": str(raw_row.get("redirect_url") or "").strip(),
        "description": str(raw_row.get("description") or "").strip(),
        "skills": [],
        "job_family": str(category.get("label") or "").strip(),
        "job_label": str(category.get("label") or "").strip(),
        "job_code": str(category.get("tag") or "").strip(),
        "public_sector": "",
        "category": str(category.get("label") or "").strip(),
        "telework": "",
        "latitude": raw_row.get("latitude"),
        "longitude": raw_row.get("longitude"),
        "raw_payload": raw_row,
    }


def collect_offres_adzuna(
    app_id: str = "",
    app_key: str = "",
    queries: list[str] | None = None,
    query_mode: str = DEFAULT_ADZUNA_QUERY_MODE,
    country: str = DEFAULT_ADZUNA_COUNTRY,
    results_per_page: int = DEFAULT_ADZUNA_RESULTS_PER_PAGE,
    max_pages: int = DEFAULT_ADZUNA_MAX_PAGES,
    timeout_seconds: int = DEFAULT_ADZUNA_TIMEOUT_SECONDS,
    require_salary: bool = DEFAULT_ADZUNA_REQUIRE_SALARY,
    exclude_predicted_salary: bool = DEFAULT_ADZUNA_EXCLUDE_PREDICTED_SALARY,
) -> list[dict[str, Any]]:
    """Point d'entree principal pour tester Adzuna."""

    if not app_id.strip() or not app_key.strip():
        print(
            "Adzuna: `ADZUNA_APP_ID` ou `ADZUNA_APP_KEY` manquant. "
            "Renseigne-les dans le `.env`."
        )
        return []

    requetes = queries or ADZUNA_QUERY_GROUPS.get(query_mode, ADZUNA_QUERY_GROUPS["focused"])
    print(
        "Adzuna: "
        f"{len(requetes)} requete(s) a lancer en mode `{query_mode}` : "
        + ", ".join(requetes)
    )

    offres: list[dict[str, Any]] = []
    identifiants_vus: set[str] = set()
    compteur_sans_salaire = 0
    compteur_salaires_predits = 0

    for query in requetes:
        total_count_annonce: int | None = None

        for page_number in range(1, max_pages + 1):
            try:
                resultats, total_count = telecharger_page_adzuna(
                    app_id=app_id,
                    app_key=app_key,
                    query=query,
                    country=country,
                    page_number=page_number,
                    results_per_page=results_per_page,
                    timeout_seconds=timeout_seconds,
                )
            except requests.RequestException as exc:
                print(f"Adzuna: echec HTTP pour la requete '{query}' page {page_number} : {exc}")
                break

            if total_count is not None:
                total_count_annonce = total_count

            print(
                "Adzuna: "
                f"query='{query}' page={page_number} rows={len(resultats)} "
                f"count={total_count_annonce if total_count_annonce is not None else 'n/a'}"
            )

            if not resultats:
                break

            for raw_row in resultats:
                if require_salary and not a_un_salaire_adzuna(raw_row):
                    compteur_sans_salaire += 1
                    continue

                if exclude_predicted_salary and est_salaire_predit_adzuna(raw_row):
                    compteur_salaires_predits += 1
                    continue

                offre = mapper_offre_adzuna(raw_row)
                external_id = str(offre.get("external_id") or "").strip()
                if not external_id or external_id in identifiants_vus:
                    continue

                identifiants_vus.add(external_id)
                offres.append(offre)

            if len(resultats) < results_per_page:
                break

    if require_salary:
        print(
            f"Adzuna: {compteur_sans_salaire} annonce(s) ignoree(s) sans salaire exploitable."
        )

    if exclude_predicted_salary:
        print(
            "Adzuna: "
            f"{compteur_salaires_predits} annonce(s) ignoree(s) car salaire predit."
        )

    print(
        f"Adzuna: {len(offres)} offre(s) unique(s) retenue(s) apres deduplication."
    )
    return offres


def build_argument_parser() -> argparse.ArgumentParser:
    """Construire le parseur CLI du collecteur Adzuna."""

    parser = argparse.ArgumentParser(
        description="Tester la source Adzuna de facon isolee.",
    )
    parser.add_argument(
        "--query",
        action="append",
        default=None,
        help="Requete Adzuna. Peut etre repetee.",
    )
    parser.add_argument(
        "--query-mode",
        choices=sorted(ADZUNA_QUERY_GROUPS),
        default=None,
        help="Strategie de requetes si `--query` n'est pas fournie.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Nombre maximum de pages a lire par requete.",
    )
    parser.add_argument(
        "--results-per-page",
        type=int,
        default=None,
        help="Nombre de resultats par page (max officiel observe : 50).",
    )
    parser.add_argument(
        "--allow-no-salary",
        action="store_true",
        help="Conserver aussi les annonces Adzuna sans salaire structure.",
    )
    parser.add_argument(
        "--exclude-predicted-salary",
        action="store_true",
        help="Ignorer les salaires marques comme predits par Adzuna.",
    )
    parser.add_argument(
        "--save-raw",
        action="store_true",
        help="Sauvegarder la collecte brute Adzuna dans `data/raw/`.",
    )
    return parser


def main() -> None:
    """Executer le collecteur Adzuna en mode isole."""

    import os

    charger_variables_environnement_locales()
    parser = build_argument_parser()
    args = parser.parse_args()

    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    query_mode = args.query_mode or os.getenv(
        "ADZUNA_QUERY_MODE",
        DEFAULT_ADZUNA_QUERY_MODE,
    )
    country = os.getenv("ADZUNA_COUNTRY", DEFAULT_ADZUNA_COUNTRY)
    results_per_page = args.results_per_page or int(
        os.getenv("ADZUNA_RESULTS_PER_PAGE", str(DEFAULT_ADZUNA_RESULTS_PER_PAGE))
    )
    max_pages = args.max_pages or int(
        os.getenv("ADZUNA_MAX_PAGES", str(DEFAULT_ADZUNA_MAX_PAGES))
    )
    timeout_seconds = int(
        os.getenv("ADZUNA_TIMEOUT_SECONDS", str(DEFAULT_ADZUNA_TIMEOUT_SECONDS))
    )
    require_salary = not args.allow_no_salary and lire_booleen_adzuna(
        os.getenv("ADZUNA_REQUIRE_SALARY"),
        DEFAULT_ADZUNA_REQUIRE_SALARY,
    )
    exclude_predicted_salary = args.exclude_predicted_salary or lire_booleen_adzuna(
        os.getenv("ADZUNA_EXCLUDE_PREDICTED_SALARY"),
        DEFAULT_ADZUNA_EXCLUDE_PREDICTED_SALARY,
    )

    offres = collect_offres_adzuna(
        app_id=app_id,
        app_key=app_key,
        queries=args.query,
        query_mode=query_mode,
        country=country,
        results_per_page=results_per_page,
        max_pages=max_pages,
        timeout_seconds=timeout_seconds,
        require_salary=require_salary,
        exclude_predicted_salary=exclude_predicted_salary,
    )
    if args.save_raw:
        output_path = sauvegarder_collecte_brute_adzuna(offres)
        print(f"Adzuna: collecte brute sauvegardee: {output_path}")
    print(f"Adzuna: {len(offres)} offre(s) retournee(s) par le collecteur.")


if __name__ == "__main__":
    main()
