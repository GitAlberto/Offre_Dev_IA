# Dossier `data/source_csv`

Ce dossier accueille les vraies sources CSV d'offres d'emploi utilisees par le
pipeline.

Source actuellement retenue :
- `BPCE` comme source CSV principale ;
- `Region Ile-de-France` comme deuxieme source CSV exploitable ;
- `Choisir le Service Public` reste disponible en complement si besoin.

Convention recommandee :
- le collecteur principal peut telecharger ici automatiquement le dernier CSV
  officiel BPCE ;
- un deuxieme collecteur peut telecharger ici automatiquement le CSV officiel
  des offres Region Ile-de-France ;
- si besoin, on peut aussi deposer manuellement un fichier telecharge ;
- les noms recommandes sont `bpce.csv` pour la source principale et
  `region_ile_de_france.csv` / `choisir_service_public.csv` pour les sources secondaires.

Si le nom telecharge contient une date et change d'une semaine a l'autre, le
collecteur sait aussi :
- lire un chemin explicite passe par `--bpce-csv-path` ;
- lire un chemin explicite passe par `--region-ile-de-france-csv-path` ;
- ou prendre automatiquement le CSV le plus recent du dossier.
