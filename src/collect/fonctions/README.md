# Dossier `src/collect/fonctions`

Ce dossier contient un connecteur par source technique.

## Connecteurs actifs

- `collect_offres_france_travail.py`
- `collect_offres_welcome_to_the_jungle.py`
- `collect_offres_bpce.py`
- `collect_offres_region_ile_de_france.py`
- `collect_offres_postgresql_history.py`
- `collect_aggregates_hive.py`

## Connecteur auxiliaire utile

- `collect_offres_adzuna.py`

Ce dernier n'entre pas dans l'orchestrateur principal. Il sert a alimenter la
simulation PostgreSQL avant relecture via `postgresql_history`.

## Convention de nommage

- `collect_offres_*` pour les sources qui renvoient des offres d'emploi
- `collect_aggregates_*` pour les sources analytiques ou pre-calculees

## Etat actuel

- `collect_offres_france_travail.py` interroge l'API France Travail
- `collect_offres_welcome_to_the_jungle.py` scrape WTTJ avec Selenium
- `collect_offres_bpce.py` lit le CSV officiel BPCE
- `collect_offres_region_ile_de_france.py` lit le CSV officiel de la Region
  Ile-de-France
- `collect_offres_postgresql_history.py` relit la table PostgreSQL `offres`
- `collect_aggregates_hive.py` relit les agregats Hive, avec repli `beeline` si
  `PyHive` echoue
- `collect_offres_adzuna.py` permet de constituer le snapshot source pour
  PostgreSQL
