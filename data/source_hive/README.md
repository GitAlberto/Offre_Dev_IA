# Donnees source Hive

Ce dossier accueille les datasets volumineux utilises pour la source Big Data.

Regles retenues :
- les fichiers telecharges ici ne sont pas versionnes dans Git ;
- on garde un sous-dossier par dataset ;
- Hive lit ces fichiers via le montage Docker `/opt/hive/ext-data`.

Premier dataset retenu :
- `eu_tech_jobs/latest/jobs.parquet`
