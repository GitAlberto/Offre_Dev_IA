# Dossier `src/transform/aggregate`

Ce dossier contient l'orchestrateur final de la phase de transformation.

## Role du dossier

Ici, on ne fait plus une petite operation isolee.

Ce dossier a pour role de :
- appeler les modules de `src/transform/nettoyage/` dans le bon ordre ;
- rassembler les sorties de ces etapes ;
- produire le dataset final consolide ;
- preparer la future sortie vers `data/processed/clean_dataset.csv`.

Ordre attendu des appels :
- `etape_1_filtrage.py`
- `etape_2_normalisation.py`
- `etape_3_deduplication.py`

## Qui doit appeler ce dossier

Le point d'entree de ce dossier doit etre appele par :
- `src/pipeline.py` dans le flux complet ;
- ou par un test d'integration si l'on veut verifier la transformation
  complete sans lancer toute l'API.

## Fichier attendu

- `aggregate.py` : orchestrateur de la phase C3
