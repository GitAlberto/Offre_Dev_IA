# Dossier `database`

Ce dossier regroupe la persistance SQL et Big Data du projet.

## PostgreSQL

La source `postgresql_history` relit la table `offres` deja alimentee par le
projet.

Fichiers utiles :
- `migrations/001_create_offres.sql` : creation de la table denormalisee `offres`
- `import_offres_postgresql.py` : import de snapshots JSON bruts vers PostgreSQL
- `alimenter_postgresql_depuis_adzuna.py` : collecte Adzuna puis injection
  directe en base pour simuler la source SQL

Flux courant pour PostgreSQL :
1. lancer `docker-compose up -d postgres`
2. alimenter la table avec Adzuna :

```powershell
python database/alimenter_postgresql_depuis_adzuna.py --truncate-first
```

3. verifier ensuite la source SQL :

```powershell
python src/collect/collect.py --only-source postgresql_history --no-save
```

Import manuel d'un snapshot brut :

```powershell
python database/import_offres_postgresql.py --input-path data/raw/adzuna_YYYYMMDD_HHMMSS.json --source adzuna
```

## Hive

La source `hive_aggregates` s'appuie sur le dataset `eu-tech-jobs` charge dans
Hive puis interrogeable via Hue.

Fichiers utiles :
- `alimenter_hive_depuis_eu_tech_jobs.py` : telechargement et chargement du
  dataset dans Hive
- `queries/hive/load_eu_tech_jobs.hql` : creation des objets Hive
- `queries/hive/extraction_hive.hql` : requete d'agregation relue par le projet
