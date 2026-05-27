# Dossier `src/transform`

Ce dossier regroupe toute la transformation des donnees entre la collecte brute
et le dataset final pret a etre importe ou expose.

## Pourquoi ce dossier existe

Le mot `aggregate` tout seul etait trop large et pouvait vouloir dire plusieurs
choses a la fois :
- nettoyer des lignes corrompues ;
- normaliser les dates, salaires et competences ;
- dedoublonner des offres venant de plusieurs sources ;
- fusionner le tout en un seul dataset final.

Pour eviter cette confusion, on separe maintenant deux sous-etapes :
- `nettoyage/` : sous-etapes du nettoyage des donnees ;
- `aggregate/` : orchestration et fusion finale.

## Convention de nommage dans `nettoyage/`

Les fichiers de `nettoyage/` portent un numero d'ordre visible dans leur nom.

Convention retenue :
- `etape_1_filtrage.py`
- `etape_2_normalisation.py`
- `etape_3_deduplication.py`

Pourquoi ce format :
- le numero rend l'ordre de passage immediatement visible ;
- le prefixe `etape_` reste compatible avec les imports Python ;
- la lecture de l'arborescence devient plus claire pour le developpement comme
  pour la soutenance.

## Flux attendu

Le flux cible est le suivant :
1. `src/collect/collect.py` recupere les donnees brutes depuis `src/collect/fonctions/`.
2. `src/transform/nettoyage/etape_1_filtrage.py` elimine ou corrige les lignes
   brutes inutilisables.
3. `src/transform/nettoyage/etape_2_normalisation.py` harmonise les formats et les
   noms de champs utiles.
4. `src/transform/nettoyage/etape_3_deduplication.py` retire les doublons entre
   sources lorsque les enregistrements sont comparables.
5. `src/transform/aggregate/aggregate.py` assemble la sortie finale et prepare
   `data/processed/clean_dataset.csv`.

## Sorties attendues

Dans cette phase, on distingue deux niveaux :
- les sorties intermediaires en memoire, qui circulent de fonction en fonction ;
- la sortie finale persistante du dataset nettoye.

La sortie finale attendue est :
- `data/processed/clean_dataset.csv`
