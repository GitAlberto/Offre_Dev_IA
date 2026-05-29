# Dossier `src/transform/nettoyage`

Ce dossier contient la vraie logique de nettoyage appliquee juste apres la
collecte brute.

## Role du dossier

Ici, on ne fait pas encore l'export final.
On prepare les donnees pour qu'elles deviennent comparables, evaluables et
dedoublonnables.

Les trois etapes sont :
- `etape_1_filtrage.py` : filtrage metier et technique ;
- `etape_2_normalisation.py` : projection dans un schema canonique commun ;
- `etape_3_deduplication.py` : regroupement et fusion des doublons.

## Strategie retenue

La strategie de nettoyage est volontairement exigeante.

### 1. Filtrage

Le filtrage ne se limite pas a supprimer les lignes vides.
Il applique aussi :
- un controle du type d'enregistrement ;
- un filtrage metier data / IA / BI / cloud ;
- une separation explicite entre vraies offres et agregats Hive ;
- un score de perimetre pour documenter pourquoi une ligne est gardee.

Cette etape est faite pour privilegier la precision plutot que le volume brut.

### 2. Normalisation

La normalisation met toutes les sources dans un vocabulaire commun :
- dates converties vers un format ISO ;
- salaires projetes vers `salary_min_normalized` / `salary_max_normalized` ;
- URL canonisees ;
- contrats et teletravail harmonises ;
- competences converties en liste propre ;
- signatures de titre, entreprise et localisation preparees pour la
  deduplication.

Cette etape calcule aussi un score de completude et un score de preference de
source pour arbitrer proprement les doublons.

### 3. Deduplication

La deduplication ne fait pas qu'eliminer.
Elle essaye de fusionner intelligemment les informations utiles :
- blocage par URL ou signatures proches ;
- comparaison par similarite de texte ;
- conservation de la meilleure version d'une offre ;
- fusion des competences et des identifiants externes ;
- preservation des informations de provenance ;
- remplacement d'un salaire predit par un salaire meilleur si une autre source
  fournit plus fiable.

## Qui appelle ces fichiers

Ces modules sont appeles par :
- `src/transform/aggregate/aggregate.py` dans le flux normal ;
- ou par des tests ponctuels si l'on veut verifier une etape isolee.

## Ce que ces fichiers renvoient

La sortie attendue ici est une sortie intermediaire en memoire :
- des `dict` ou `list[dict]` enrichis ;
- deja normalises et traces ;
- mais pas encore exportes eux-memes en CSV final.

## Fichier utilitaire

Le module `utils.py` centralise les briques transverses du nettoyage :
- normalisation texte ;
- parsing de dates ;
- parsing de salaires ;
- evaluation du perimetre metier ;
- aides a la deduplication ;
- score de completude.
