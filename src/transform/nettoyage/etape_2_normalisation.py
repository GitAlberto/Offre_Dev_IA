"""Etape 2 : normalisation canonique des enregistrements filtres."""

from __future__ import annotations

from typing import Any

from .utils import (
    AGGREGATE_SOURCE_NAMES,
    SOURCE_PRIORITY,
    calculer_completeness_score,
    convertir_vers_datetime_iso,
    decouper_texte_signature,
    extraire_infos_salaire,
    nettoyer_texte,
    normaliser_liste_competences,
    normaliser_teletravail,
    normaliser_texte_match,
    normaliser_type_contrat,
    normaliser_url,
)


def normaliser_ligne_source(
    nom_source: str,
    ligne_filtree: dict[str, Any],
) -> dict[str, Any]:
    """Normaliser une ligne provenant d'une source precise."""

    if nom_source in AGGREGATE_SOURCE_NAMES:
        count_value = ligne_filtree.get("count") or ligne_filtree.get("nb")
        try:
            count_normalized = int(count_value)
        except (TypeError, ValueError):
            count_normalized = 0

        return {
            **dict(ligne_filtree),
            "source": nom_source,
            "record_kind": "aggregate",
            "competence": nettoyer_texte(ligne_filtree.get("competence")),
            "region": nettoyer_texte(ligne_filtree.get("region")),
            "count": count_normalized,
            "normalization_status": "normalized_aggregate",
        }

    ligne_normalisee = dict(ligne_filtree)
    ligne_normalisee["source"] = nom_source
    ligne_normalisee["record_kind"] = "offer"
    ligne_normalisee["origin_source"] = nettoyer_texte(
        ligne_filtree.get("origin_source")
    ) or nom_source

    title = nettoyer_texte(ligne_filtree.get("title"))
    company_name = nettoyer_texte(
        ligne_filtree.get("company_name") or ligne_filtree.get("company")
    )
    location_label = nettoyer_texte(
        ligne_filtree.get("location_label") or ligne_filtree.get("location")
    )
    description = nettoyer_texte(ligne_filtree.get("description"))
    skills_normalized = normaliser_liste_competences(ligne_filtree.get("skills"))
    contract_type_normalized = normaliser_type_contrat(
        ligne_filtree.get("contract_type")
    )
    telework_normalized = normaliser_teletravail(
        ligne_filtree.get("telework")
        or ligne_filtree.get("remote_policy")
        or ligne_filtree.get("weekly_work_duration")
    )
    published_at_iso, published_date = convertir_vers_datetime_iso(
        ligne_filtree.get("published_at")
    )
    application_deadline_iso, _ = convertir_vers_datetime_iso(
        ligne_filtree.get("application_deadline")
    )
    salary_info = extraire_infos_salaire(ligne_filtree)

    ligne_normalisee.update(
        {
            "external_id": nettoyer_texte(ligne_filtree.get("external_id")),
            "title": title,
            "company_name": company_name,
            "company": company_name,
            "location_label": location_label,
            "location": location_label,
            "description": description,
            "skills": skills_normalized,
            "skills_normalized": skills_normalized,
            "contract_type": nettoyer_texte(ligne_filtree.get("contract_type")),
            "contract_type_normalized": contract_type_normalized,
            "telework_normalized": telework_normalized,
            "url": nettoyer_texte(ligne_filtree.get("url")),
            "application_url": nettoyer_texte(ligne_filtree.get("application_url")),
            "url_canonical": normaliser_url(
                ligne_filtree.get("application_url") or ligne_filtree.get("url")
            ),
            "published_at": published_at_iso,
            "published_date": published_date,
            "application_deadline": application_deadline_iso,
            "title_normalized": normaliser_texte_match(title),
            "company_normalized": normaliser_texte_match(company_name),
            "location_normalized": normaliser_texte_match(location_label),
            "title_signature": decouper_texte_signature(title),
            "company_signature": decouper_texte_signature(company_name, max_tokens=4),
            "location_signature": decouper_texte_signature(location_label, max_tokens=4),
            "source_priority": SOURCE_PRIORITY.get(nom_source, 0),
            "normalization_status": "normalized_offer",
        }
    )
    ligne_normalisee.update(salary_info)
    ligne_normalisee["completeness_score"] = calculer_completeness_score(
        ligne_normalisee
    )
    ligne_normalisee["record_preference_score"] = (
        ligne_normalisee["source_priority"] + ligne_normalisee["completeness_score"]
    )

    return ligne_normalisee


def normaliser_payloads_filtres(
    payloads_filtres_par_source: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Normaliser l'ensemble des payloads filtres."""

    payloads_normalises: dict[str, list[dict[str, Any]]] = {}

    for nom_source, lignes_filtrees in payloads_filtres_par_source.items():
        payloads_normalises[nom_source] = [
            normaliser_ligne_source(
                nom_source=nom_source,
                ligne_filtree=ligne_filtree,
            )
            for ligne_filtree in lignes_filtrees
        ]

    return payloads_normalises
