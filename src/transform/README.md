# Dossier `src/transform`

Ce dossier contient toute la phase C3 : transformer les sorties brutes
heterogenes en un dataset final d'offres comparable, dedoublonne et exploitable.

## Architecture retenue

La transformation est volontairement separee en deux couches :
- `nettoyage/` : logique metier detaillee ligne par ligne ;
- `aggregate/` : orchestration finale du pipeline de transformation.

Cette separation evite de melanger :
- le filtrage du bruit ;
- la normalisation canonique ;
- la deduplication inter-sources ;
- la preparation du dataset final.

## Strategie de nettoyage

La strategie retenue est volontairement stricte et orientee qualite :
- on conserve uniquement les lignes qui ressemblent a de vraies offres ;
- on filtre le perimetre metier data / IA / BI / cloud avec un score et des
  indices de pertinence ;
- on harmonise ensuite les dates, salaires, contrats, URL et competences dans
  un schema commun ;
- on dedoublonne enfin les offres comparables avec une logique de blocage, de
  similarite et de fusion d'information.

Le but n'est pas de garder le maximum de lignes brutes.
Le but est d'obtenir un dataset final defendable, coherent et exploitable.

## Convention de nommage dans `nettoyage/`

Les fichiers de `nettoyage/` portent un numero d'ordre visible :
- `etape_1_filtrage.py`
- `etape_2_normalisation.py`
- `etape_3_deduplication.py`

Ce choix rend l'ordre logique immediatement lisible dans l'arborescence, dans
les imports Python et pendant la soutenance.

## Flux cible

Le flux cible est le suivant :
1. `src/collect/collect.py` recupere les donnees brutes multi-sources.
2. `src/transform/nettoyage/etape_1_filtrage.py` retire les lignes invalides,
   les lignes hors perimetre et les agregats incomplets.
3. `src/transform/nettoyage/etape_2_normalisation.py` projette les lignes
   retenues dans un schema canonique commun.
4. `src/transform/nettoyage/etape_3_deduplication.py` regroupe les annonces
   comparables et fusionne les doublons.
5. `src/transform/aggregate/aggregate.py` assemble uniquement les vraies offres
   dans le dataset final et ignore les agregats Hive pour cette sortie.

## Sorties attendues

Dans cette phase, on distingue :
- les sorties intermediaires en memoire, qui circulent entre fonctions ;
- la sortie finale persistante du dataset nettoye.

La destination cible documentee est :
- `data/processed/clean_dataset.csv`

## Sources traitees par la transformation

Les vraies sources d'offres attendues dans le nettoyage sont :
- `france_travail`
- `welcome_to_the_jungle`
- `bpce`
- `region_ile_de_france`
- `postgresql_history`

La source `hive_aggregates` est acceptee dans la phase de nettoyage mais reste
un objet metier different : ce sont des agregats analytiques, pas des offres.
