"""Etape 3 : deduplication experte avec fusion des doublons."""

from __future__ import annotations

from typing import Any

from .utils import (
    choisir_meilleur_texte,
    construire_blocs_deduplication,
    fusionner_competences,
    nettoyer_texte,
    sont_doublons,
)


def construire_cle_deduplication(offre_normalisee: dict[str, Any]) -> tuple[Any, ...]:
    """Construire une cle simple de debug pour une offre normalisee."""

    return (
        offre_normalisee.get("url_canonical"),
        offre_normalisee.get("title_signature"),
        offre_normalisee.get("company_signature"),
        offre_normalisee.get("published_date"),
    )


def fusionner_offres_doublons(
    offre_reference: dict[str, Any],
    doublon: dict[str, Any],
) -> None:
    """Fusionner un doublon dans l'offre de reference sans perdre d'information utile."""

    offre_reference["duplicate_count"] = int(offre_reference.get("duplicate_count") or 1) + 1

    sources = list(offre_reference.get("duplicate_sources") or [offre_reference.get("source")])
    if doublon.get("source") and doublon["source"] not in sources:
        sources.append(doublon["source"])
    offre_reference["duplicate_sources"] = sources

    origin_sources = list(
        offre_reference.get("duplicate_origin_sources")
        or [offre_reference.get("origin_source") or offre_reference.get("source")]
    )
    doublon_origin = doublon.get("origin_source") or doublon.get("source")
    if doublon_origin and doublon_origin not in origin_sources:
        origin_sources.append(doublon_origin)
    offre_reference["duplicate_origin_sources"] = origin_sources

    external_ids = list(
        offre_reference.get("duplicate_external_ids")
        or [offre_reference.get("external_id")]
    )
    if doublon.get("external_id") and doublon["external_id"] not in external_ids:
        external_ids.append(doublon["external_id"])
    offre_reference["duplicate_external_ids"] = [
        external_id for external_id in external_ids if external_id
    ]

    for champ in (
        "title",
        "company_name",
        "company",
        "location_label",
        "location",
        "contract_type",
        "contract_type_normalized",
        "telework_normalized",
        "published_at",
        "published_date",
        "application_deadline",
        "url",
        "application_url",
        "url_canonical",
        "job_family",
        "job_label",
        "job_code",
        "category",
    ):
        if not nettoyer_texte(offre_reference.get(champ)):
            offre_reference[champ] = doublon.get(champ)

    offre_reference["description"] = choisir_meilleur_texte(
        offre_reference.get("description"),
        doublon.get("description"),
    )
    offre_reference["salary"] = choisir_meilleur_texte(
        offre_reference.get("salary"),
        doublon.get("salary"),
    )

    if (
        not offre_reference.get("salary_currency")
        and doublon.get("salary_currency")
    ):
        offre_reference["salary_currency"] = doublon.get("salary_currency")
    if (
        not offre_reference.get("salary_period")
        and doublon.get("salary_period")
    ):
        offre_reference["salary_period"] = doublon.get("salary_period")

    reference_predite = bool(offre_reference.get("salary_is_predicted"))
    doublon_predit = bool(doublon.get("salary_is_predicted"))
    if (
        offre_reference.get("salary_min_normalized") is None
        and doublon.get("salary_min_normalized") is not None
    ) or (
        reference_predite and not doublon_predit
    ):
        offre_reference["salary_min_normalized"] = doublon.get("salary_min_normalized")
        offre_reference["salary_max_normalized"] = doublon.get("salary_max_normalized")
        offre_reference["salary_is_predicted"] = doublon.get("salary_is_predicted")

    offre_reference["skills_normalized"] = fusionner_competences(
        offre_reference.get("skills_normalized") or [],
        doublon.get("skills_normalized") or [],
    )
    offre_reference["skills"] = offre_reference["skills_normalized"]

    offre_reference["completeness_score"] = max(
        int(offre_reference.get("completeness_score") or 0),
        int(doublon.get("completeness_score") or 0),
    )
    offre_reference["record_preference_score"] = max(
        int(offre_reference.get("record_preference_score") or 0),
        int(doublon.get("record_preference_score") or 0),
    )
    offre_reference["deduplication_status"] = "merged_duplicate"


def dedoublonner_offres_normalisees(
    offres_normalisees: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Retirer les doublons evidents et fusionner les informations utiles."""

    offres_tries = sorted(
        (dict(offre) for offre in offres_normalisees if isinstance(offre, dict)),
        key=lambda offre: (
            int(offre.get("record_preference_score") or 0),
            int(offre.get("scope_score") or 0),
            int(offre.get("completeness_score") or 0),
        ),
        reverse=True,
    )

    index_blocs: dict[str, list[int]] = {}
    offres_uniques: list[dict[str, Any]] = []

    for offre in offres_tries:
        candidates_indexes: set[int] = set()
        for bloc in construire_blocs_deduplication(offre):
            for index in index_blocs.get(bloc, []):
                candidates_indexes.add(index)

        reference_trouvee: dict[str, Any] | None = None
        for index in sorted(candidates_indexes):
            candidate = offres_uniques[index]
            if sont_doublons(candidate, offre):
                reference_trouvee = candidate
                break

        if reference_trouvee is None:
            offre["duplicate_count"] = 1
            offre["duplicate_sources"] = [offre.get("source")]
            offre["duplicate_origin_sources"] = [
                offre.get("origin_source") or offre.get("source")
            ]
            offre["duplicate_external_ids"] = [
                offre.get("external_id")
            ] if offre.get("external_id") else []
            offre["deduplication_status"] = "unique"
            offres_uniques.append(offre)
            nouvel_index = len(offres_uniques) - 1
            for bloc in construire_blocs_deduplication(offre):
                index_blocs.setdefault(bloc, []).append(nouvel_index)
            continue

        fusionner_offres_doublons(reference_trouvee, offre)

    print(
        "Nettoyage deduplication: "
        f"{len(offres_normalisees)} offre(s) comparee(s), "
        f"{len(offres_uniques)} offre(s) unique(s) retenue(s)."
    )
    return offres_uniques
