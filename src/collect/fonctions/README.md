# Dossier `src/collect/fonctions`

Ce dossier centralise les fonctions techniques de collecte par source.

L'idee de cette couche est simple :
- `src/collect/collect.py` joue le role d'orchestrateur de collecte ;
- cet orchestrateur appellera les fonctions definies ici ;
- chaque fichier de ce dossier sera responsable d'une seule source bien precise ;
- chaque source renverra des donnees brutes ou semi-structurees ;
- `src/transform/nettoyage/` prendra ensuite le relais pour le nettoyage au sens large ;
- `src/transform/aggregate/aggregate.py` construira ensuite le dataset final agrege.

## Regle d'architecture

Chaque fichier de ce dossier doit :
- correspondre a une seule source ;
- exposer une fonction principale de collecte ;
- expliquer clairement ce qu'il appelle en interne ;
- expliquer clairement ce qui est cense l'appeler depuis le pipeline ;
- rester focalise sur la collecte, sans melanger la logique metier de nettoyage,
  de normalisation ou d'agregation.

## Fichiers attendus

- `collect_offres_france_travail.py`
- `collect_offres_welcome_to_the_jungle.py`
- `collect_offres_la_bonne_alternance.py`
- `collect_offres_bpce.py`
- `collect_offres_region_ile_de_france.py`
- `collect_offres_postgresql_history.py`
- `collect_aggregates_hive.py`

## Convention de nommage

Le nom des fichiers doit dire immediatement quel type de donnees ils
collectent :
- `collect_offres_*` pour les sources qui renvoient des offres d'emploi ;
- `collect_reference_*` pour les sources de referentiel ;
- `collect_aggregates_*` pour les sources analytiques pre-calculees.

Cette convention rend la lecture beaucoup plus claire :
- pendant le developpement ;
- pendant la soutenance ;
- et pendant la maintenance du projet.

## Etat actuel

Dans l'etat actuel du projet :
- `collect_offres_france_travail.py` est le premier connecteur qui contient un
  vrai flux exploitable ;
- il sait demander un token OAuth, appeler l'API des offres et mapper les
  reponses quand les identifiants sont disponibles ;
- il sait aussi utiliser un secours local en mode demo si on ajoute plus tard
  un fichier `data/fallback/fallback_france_travail.json` ou `.csv` ;
- `collect_offres_welcome_to_the_jungle.py` sait scraper des pages metier WTTJ
  avec Selenium ;
- `collect_offres_la_bonne_alternance.py` sait recuperer l'export JSON officiel
  LBA sur jeton puis filtrer le perimetre data / IA / BI / cloud ;
- `collect_offres_bpce.py` sait telecharger puis lire le CSV officiel riche
  des offres Groupe BPCE ;
- `collect_offres_region_ile_de_france.py` sait telecharger puis lire le CSV
  officiel des offres de la Region Ile-de-France ;
- `collect_offres_choisir_service_public.py` reste disponible comme source CSV
  secondaire plus volumineuse mais moins detaillee ;
- `collect_offres_postgresql_history.py` sait relire la table PostgreSQL `offres`
  deja alimentee par le projet ;
- Hive reste encore au stade squelette documente.

## Flux prevu

Le flux cible sera le suivant :
- `src/pipeline.py` lance la chaine complete ;
- `src/collect/collect.py` orchestre la collecte multi-sources ;
- `src/collect/fonctions/*.py` collectent chaque source de maniere isolee ;
- `src/transform/nettoyage/*.py` filtrent, normalisent et dedoublonnent ;
- `src/transform/aggregate/aggregate.py` fusionne les sorties transformees ;
- `database/import_offres_postgresql.py` importe ensuite les JSON bruts choisis
  dans PostgreSQL.

## Ou retrouver la sortie d'un fichier de collect

Il faut distinguer deux types de sortie :
- la sortie immediate de la fonction ;
- la sortie persistante ecrite sur disque.

### Sortie immediate

Par defaut, un fichier de `src/collect/fonctions/` est cense renvoyer une structure en
memoire, generalement une `list[dict]`.

Cette sortie est recuperable :
- directement dans la valeur de retour de la fonction principale ;
- depuis `src/collect/collect.py`, qui est cense appeler ces fonctions ;
- puis depuis `src/pipeline.py`, si le pipeline complet est lance.

### Sortie ecrite sur disque

Les fichiers de `src/collect/fonctions/` ne sont pas censes ecrire eux-memes le
dataset final nettoye.

Si une sortie brute est sauvegardee apres collecte, elle doit etre retrouvee
dans :
- `data/raw/`

Convention retenue :
- sortie brute consolidee de toutes les sources : `data/raw/raw_YYYYMMDD_HHMMSS.json`
- sortie brute d'une seule source : `data/raw/<nom_source>_YYYYMMDD_HHMMSS.json`

Exemples :
- `data/raw/raw_20260526_221500.json`
- `data/raw/france_travail_20260526_221500.json`
- `data/raw/welcome_to_the_jungle_20260526_221500.json`

### Sortie apres nettoyage

Une fois la collecte terminee, la sortie nettoyee ne se retrouve plus dans
`src/collect/fonctions/` mais dans :
- `data/processed/`

Le fichier cible prevu par la roadmap est :
- `data/processed/clean_dataset.csv`
