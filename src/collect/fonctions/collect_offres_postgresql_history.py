"""Module de lecture de l'historique des offres stockees dans PostgreSQL.

Ce module a pour responsabilites :
- interroger la table PostgreSQL `offres` deja alimentee par le projet ;
- relire les offres recentes pour servir de source historique ;
- remapper les lignes SQL vers le schema brut interne du pipeline.
"""

from __future__ import annotations

from typing import Any

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - repli simple si psycopg manque
    psycopg = None
    dict_row = None


def build_postgresql_history_query(days_back: int = 30) -> tuple[str, tuple[int, ...]]:
    """Construire la requete SQL utilisee pour lire l'historique recent."""

    query = """
        SELECT
            source,
            external_id,
            title,
            company,
            company_name,
            location,
            location_label,
            contract_type,
            COALESCE(published_at_raw, published_at::text, '') AS published_at,
            COALESCE(application_deadline_raw, application_deadline::text, '') AS application_deadline,
            salary,
            salary_min,
            salary_max,
            salary_is_predicted,
            url,
            application_url,
            description,
            skills,
            job_family,
            job_label,
            job_code,
            public_sector,
            category,
            telework,
            contract_time,
            raw_payload
        FROM offres
        WHERE published_at IS NULL
           OR published_at >= NOW() - (%s * INTERVAL '1 day')
        ORDER BY published_at DESC NULLS LAST, imported_at DESC
    """
    return query, (max(days_back, 0),)


def map_postgresql_history_row(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Convertir une ligne PostgreSQL vers le schema brut de source du projet."""

    company_name = str(
        raw_row.get("company_name") or raw_row.get("company") or ""
    ).strip()
    location_label = str(
        raw_row.get("location_label") or raw_row.get("location") or ""
    ).strip()

    return {
        "source": "postgresql_history",
        "origin_source": raw_row.get("source"),
        "external_id": raw_row.get("external_id"),
        "title": raw_row.get("title"),
        "company": company_name,
        "company_name": company_name,
        "location": location_label,
        "location_label": location_label,
        "salary": raw_row.get("salary"),
        "salary_min": raw_row.get("salary_min"),
        "salary_max": raw_row.get("salary_max"),
        "salary_is_predicted": raw_row.get("salary_is_predicted"),
        "contract_type": raw_row.get("contract_type"),
        "contract_time": raw_row.get("contract_time"),
        "published_at": raw_row.get("published_at"),
        "application_deadline": raw_row.get("application_deadline"),
        "url": raw_row.get("url"),
        "application_url": raw_row.get("application_url"),
        "description": raw_row.get("description"),
        "skills": raw_row.get("skills") if isinstance(raw_row.get("skills"), list) else [],
        "job_family": raw_row.get("job_family"),
        "job_label": raw_row.get("job_label"),
        "job_code": raw_row.get("job_code"),
        "public_sector": raw_row.get("public_sector"),
        "category": raw_row.get("category"),
        "telework": raw_row.get("telework"),
        "raw_payload": raw_row.get("raw_payload") if isinstance(raw_row.get("raw_payload"), dict) else {},
    }


def collect_offres_postgresql_history(
    database_url: str = "",
    days_back: int = 30,
    use_demo_seed: bool = True,
) -> list[dict[str, Any]]:
    """Lire les offres recentes deja presentes dans PostgreSQL."""

    if psycopg is None or dict_row is None:
        print(
            "PostgreSQL history: `psycopg` n'est pas installe, lecture historique ignoree."
        )
        return []

    if not database_url.strip():
        print("PostgreSQL history: `DATABASE_URL` est vide, lecture historique ignoree.")
        return []

    query, query_params = build_postgresql_history_query(days_back=days_back)
    _ = use_demo_seed

    try:
        with psycopg.connect(database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, query_params)
                lignes = cursor.fetchall()
    except psycopg.Error as exc:
        print(f"PostgreSQL history: echec de lecture SQL : {exc}")
        return []

    offres = [map_postgresql_history_row(raw_row) for raw_row in lignes]
    print(
        "PostgreSQL history: "
        f"{len(offres)} offre(s) relue(s) depuis la table `offres` sur {days_back} jour(s)."
    )
    return offres
