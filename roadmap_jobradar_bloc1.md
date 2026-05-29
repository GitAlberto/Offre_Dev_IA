# Roadmap Bloc 1

Ce document sert de feuille de route courte et a jour pour le bloc 1.

## Sources retenues

- API : `France Travail`
- Scraping : `Welcome to the Jungle`
- CSV : `BPCE`
- CSV : `Region Ile-de-France`
- Base de donnees : `PostgreSQL` simule avec un snapshot `Adzuna`
- Big Data : `Hive` simule avec `eu-tech-jobs`, interrogeable via `Hue`

## Architecture actuelle

### Collecte brute

- `src/collect/collect.py`
- `src/collect/fonctions/collect_offres_france_travail.py`
- `src/collect/fonctions/collect_offres_welcome_to_the_jungle.py`
- `src/collect/fonctions/collect_offres_bpce.py`
- `src/collect/fonctions/collect_offres_region_ile_de_france.py`
- `src/collect/fonctions/collect_offres_postgresql_history.py`
- `src/collect/fonctions/collect_aggregates_hive.py`

### Source SQL simulee

- `src/collect/fonctions/collect_offres_adzuna.py`
- `database/alimenter_postgresql_depuis_adzuna.py`
- `database/import_offres_postgresql.py`
- `database/migrations/001_create_offres.sql`

### Source Big Data simulee

- `database/alimenter_hive_depuis_eu_tech_jobs.py`
- `queries/hive/load_eu_tech_jobs.hql`
- `queries/hive/extraction_hive.hql`
- `docker/hue/hue.ini`

## Regles de cadrage

- `Adzuna` ne fait pas partie du run principal de `collect.py`
- `Adzuna` sert uniquement a peupler la source PostgreSQL simulee
- `Hive` ne renvoie pas des offres unitaires mais des agregats
- les anciennes pistes `LBA`, `Choisir le Service Public` et `ROME` ne font
  plus partie de l'architecture active

## Commandes utiles

Collecte principale :

```powershell
python src/collect/collect.py
```

Peupler PostgreSQL avec Adzuna :

```powershell
python database/alimenter_postgresql_depuis_adzuna.py --truncate-first
```

Charger Hive avec `eu-tech-jobs` :

```powershell
python database/alimenter_hive_depuis_eu_tech_jobs.py
```

## Priorite de la suite

1. figer la collecte brute de reference
2. lancer le nettoyage / filtrage C3
3. dedoublonner les offres entre sources
4. produire le dataset final consolide
