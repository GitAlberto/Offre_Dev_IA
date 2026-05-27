# Dossier `src`

Ce dossier contiendra le code source principal du pipeline.

On y retrouvera ensuite :
- des fonctions de collecte source par source dans `src/collect/fonctions/` ;
- la collecte multi-sources ;
- la transformation des donnees dans `src/transform/` ;
- l'agregation finale du dataset nettoye ;
- l'orchestration du pipeline complet.

## Decoupage retenu

Le projet est maintenant organise en trois grandes etapes de traitement :
- `src/collect/fonctions/` : une source de collecte par fichier ;
- `src/collect/` : l'orchestrateur qui appelle les collecteurs ;
- `src/transform/` : le traitement des donnees avant import en base.

Dans `src/transform/`, on separe volontairement :
- `nettoyage/` pour les sous-etapes de nettoyage des donnees ;
- `aggregate/` pour l'orchestrateur final qui fusionne le tout.

Ce decoupage rend le pipeline beaucoup plus lisible :
- collecte = on recupere ;
- nettoyage = on filtre, on normalise et on dedoublonne ;
- aggregate = on fusionne et on prepare la sortie finale.
