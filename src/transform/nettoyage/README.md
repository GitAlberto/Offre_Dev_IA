# Dossier `src/transform/nettoyage`

Ce dossier contient les sous-etapes du nettoyage applique aux donnees juste
apres la collecte brute.

## Role du dossier

Ici, on ne fait pas encore la fusion finale du dataset.

On prepare les donnees pour qu'elles deviennent comparables et exploitables :
- `etape_1_filtrage.py` retire ou corrige les lignes brutes clairement invalides ;
- `etape_2_normalisation.py` harmonise les formats et les noms utiles ;
- `etape_3_deduplication.py` compare les offres comparables pour retirer les doublons.

## Pourquoi les noms sont numerotes

Chaque nom de fichier indique explicitement l'ordre logique de traitement.

Cela permet de comprendre d'un seul coup d'oeil :
- quelle etape doit etre executee en premier ;
- quelle etape depend de la precedente ;
- dans quel ordre lire les fichiers pendant la soutenance.

## Qui appelle ces fichiers

Ces modules ne sont pas censes etre le point d'entree principal du projet.

Ils doivent etre appeles par :
- `src/transform/aggregate/aggregate.py` pour la transformation complete ;
- ou ponctuellement par des tests unitaires si on veut verifier une etape
  precise.

## Ce que ces fichiers doivent renvoyer

La sortie attendue ici est avant tout une sortie en memoire :
- des `dict` ou des `list[dict]` intermediaires ;
- deja plus propres que la collecte brute ;
- mais pas encore ecrits eux-memes comme dataset final CSV.
