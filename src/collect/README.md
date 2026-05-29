# Dossier `src/collect`

Cette couche orchestre la collecte brute multi-sources.

## Sources retenues

- `france_travail` : API France Travail
- `welcome_to_the_jungle` : scraping Selenium
- `bpce` : CSV principal
- `region_ile_de_france` : second CSV retenu
- `postgresql_history` : source base de donnees, relue depuis PostgreSQL
- `hive_aggregates` : source Big Data, relue depuis Hive

Important :
- `Adzuna` sert a remplir PostgreSQL, mais ne fait pas partie du run par defaut
  de `collect.py`
- `Hive` sert des agregats et n'alimente pas directement le dataset final
  d'offres

## Structure retournee

L'orchestrateur renvoie un `dict[str, list[dict]]` avec une cle par source.

Exemple :

```python
{
    "france_travail": [...],
    "welcome_to_the_jungle": [...],
    "bpce": [...],
    "region_ile_de_france": [...],
    "postgresql_history": [...],
    "hive_aggregates": [...],
}
```

## Sorties sur disque

- sortie brute globale : `data/raw/raw_YYYYMMDD_HHMMSS.json`
- sortie brute par source : `data/raw/<nom_source>_YYYYMMDD_HHMMSS.json`

## Commandes utiles

Run global :

```powershell
python src/collect/collect.py
```

Tests isoles :

```powershell
python src/collect/collect.py --only-source welcome_to_the_jungle
python src/collect/collect.py --only-source bpce
python src/collect/collect.py --only-source region_ile_de_france
python src/collect/collect.py --only-source postgresql_history --no-save
python src/collect/collect.py --only-source hive_aggregates --no-save
```

## Options principales

- `--demo`
- `--no-save`
- `--save-per-source`
- `--query-wttj`
- `--wttj-query-mode`
- `--bpce-csv-path`
- `--region-ile-de-france-csv-path`
- `--only-source`
- `--skip-source`
- `--days-back-postgresql`
- `--france-travail-query-mode`
- `--france-travail-max-pages`

## Variables d'environnement utiles

- `FRANCE_TRAVAIL_CLIENT_ID`
- `FRANCE_TRAVAIL_CLIENT_SECRET`
- `FRANCE_TRAVAIL_SCOPE`
- `FRANCE_TRAVAIL_QUERY_MODE`
- `FRANCE_TRAVAIL_MAX_RESULTS`
- `FRANCE_TRAVAIL_MAX_PAGES`
- `FRANCE_TRAVAIL_TIMEOUT_SECONDS`
- `WTTJ_QUERY_MODE`
- `WTTJ_MAX_PAGES`
- `WTTJ_TIMEOUT_SECONDS`
- `WTTJ_PREFLIGHT_TIMEOUT_SECONDS`
- `WTTJ_CHROME_BINARY`
- `BPCE_CSV_PATH`
- `REGION_ILE_DE_FRANCE_CSV_PATH`
- `DATABASE_URL`
- `HIVE_HOST`
- `HIVE_PORT`
- `HIVE_DATABASE`
- `HIVE_AUTH`
- `HIVE_BEELINE_CONTAINER`
