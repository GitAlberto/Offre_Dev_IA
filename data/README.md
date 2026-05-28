# Dossier `data`

Ce dossier centralisera les donnees manipulees par le pipeline.

On y separera :
- les donnees brutes collectees ;
- les donnees nettoyees ;
- les fichiers de secours et jeux de demonstration ;
- les sources CSV locales placees volontairement hors du code.

Sous-dossiers utiles :
- `raw/` : sorties JSON brutes de collecte ;
- `processed/` : jeux nettoyes ou exportes ;
- `fallback/` : secours de demonstration hors ligne ;
- `source_csv/` : depot local des vraies sources CSV d'offres, par exemple
  `bpce.csv`, `region_ile_de_france.csv` ou `choisir_service_public.csv`.
