# Dossier `database`

Ce dossier regroupe la persistance PostgreSQL du projet.

On y trouve maintenant :
- `migrations/001_create_offres.sql` : creation de la table denormalisee `offres` ;
- `import_offres_postgresql.py` : import des JSON bruts produits par l'orchestrateur ;
- `alimenter_postgresql_depuis_lba.py` : collecte LBA puis charge directement
  la table PostgreSQL.

Flux pratique retenu :
1. lancer `docker-compose up -d postgres`
2. produire un JSON brut avec `python src/collect/collect.py`
3. importer ce JSON dans PostgreSQL avec :

```powershell
python database/import_offres_postgresql.py
```

Le script prend par defaut le `data/raw/raw_*.json` le plus recent.

Commandes utiles :

```powershell
python database/import_offres_postgresql.py --create-schema-only
```

```powershell
python database/import_offres_postgresql.py --source la_bonne_alternance
```

Pont direct pour creer la source PostgreSQL a partir de LBA :

```powershell
python database/alimenter_postgresql_depuis_lba.py
```
