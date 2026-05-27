# Dossier `src/collect`

Ce dossier regroupe la phase de collecte des donnees.

Il contient deja :
- `src/collect/collect.py`, point d'entree de la collecte multi-sources ;
- la logique d'orchestration des sources ;
- les appels aux fonctions source-specifiques de `src/collect/fonctions/`.

## Role attendu

Ce dossier pilotera la collecte mais ne devra pas contenir toute la logique
technique de chaque source.

Le principe retenu est le suivant :
- `src/collect/collect.py` orchestrera la collecte ;
- il appellera les fonctions detaillees dans `src/collect/fonctions/` ;
- chaque module de `src/collect/fonctions/` sera responsable d'une seule source ;
- `src/transform/nettoyage/` prendra ensuite le relais pour nettoyer ;
- `src/transform/aggregate/aggregate.py` assemblera enfin le dataset final.

Dans l'etat actuel du projet, `src/collect/collect.py` existe deja et joue
precisement ce role d'orchestrateur.

Premier niveau de concret :
- la source `France Travail` est maintenant la premiere source avec un vrai
  connecteur HTTP exploitable ;
- les autres sources conservent encore un role de squelette documente en
  attendant leur implementation progressive.

## Ou retrouver la sortie de la collecte

Ce dossier correspond au niveau orchestrateur. Il ne decrit pas une source
unique, mais la collecte globale une fois les fonctions de `src/collect/fonctions/`
appelees.

### Sortie immediate de l'orchestrateur

Le fichier `src/collect/collect.py` recupere les retours de chaque fonction de
collecte puis produit une structure consolidee en memoire.

Cette sortie immediate est :
- un `dict[str, list[dict]]` ;
- avec une cle par source ;
- puis transmise a la suite du pipeline.

Exemple de structure retournee :

```python
{
    "france_travail": [...],
    "welcome_to_the_jungle": [...],
    "rome_reference": [...],
    "postgresql_history": [...],
    "hive_aggregates": [...],
}
```

### Sortie ecrite sur disque

Si la collecte est sauvegardee apres orchestration, il faudra retrouver cette
sortie dans :
- `data/raw/`

Convention recommandee :
- sortie brute globale : `data/raw/raw_YYYYMMDD_HHMMSS.json`
- sortie brute par source : `data/raw/<nom_source>_YYYYMMDD_HHMMSS.json`

Exemples :
- `data/raw/raw_20260526_221500.json`
- `data/raw/france_travail_20260526_221500.json`
- `data/raw/postgresql_history_20260526_221500.json`

## Comment lancer l'orchestrateur

Le point d'entree actuel est :
- `python src/collect/collect.py`

Options deja prevues :
- `--demo` : active le mode demonstration pour les sources qui prevoient un
  secours local ;
- `--no-save` : n'ecrit pas le JSON brut global ;
- `--save-per-source` : ecrit aussi un fichier brut distinct par source ;
- `--query-wttj` : permet de changer la requete Welcome to the Jungle ;
- `--days-back-postgresql` : regle la profondeur de lecture de l'historique.
- `--france-travail-query-mode` : choisit la strategie de volume France Travail
  (`legacy`, `focused`, `broad`, `max_volume`) ;
- `--france-travail-max-pages` : limite ou non le nombre de pages lues par groupe
  de mots-cles France Travail.

Variables d'environnement deja utilisees par la collecte :
- `FRANCE_TRAVAIL_CLIENT_ID`
- `FRANCE_TRAVAIL_CLIENT_SECRET`
- `FRANCE_TRAVAIL_SCOPE`
- `FRANCE_TRAVAIL_QUERY_MODE`
- `FRANCE_TRAVAIL_MAX_RESULTS`
- `FRANCE_TRAVAIL_MAX_PAGES`
- `FRANCE_TRAVAIL_TIMEOUT_SECONDS`
- `DATABASE_URL`
- `HIVE_HOST`
- `HIVE_PORT`

### Apres la collecte

Une fois la collecte terminee, `src/collect/` ne doit pas produire a lui seul
le jeu de donnees final nettoye.

La sortie normalisee finale est attendue dans :
- `data/processed/clean_dataset.csv`

Cette etape releve ensuite de `src/transform/aggregate/aggregate.py`,
qui s'appuiera lui-meme sur les modules de `src/transform/nettoyage/`.

## Strategie France Travail

Les modes disponibles n'ont pas le meme objectif :
- `legacy` : reproduit la requete historique initiale.
- `focused` : plusieurs familles de recherche encore assez strictes.
- `broad` : bon compromis volume / pertinence pour rester centre sur data / IA.
- `max_volume` : ajoute des termes plus larges comme `python`, `sql`, `tableau`
  ou `power bi` pour viser plusieurs milliers de lignes brutes, au prix d'un
  bruit metier plus fort a nettoyer ensuite.

Le mode `max_volume` integre aussi des groupes metier plus riches :
- data engineering ;
- IA / machine learning ;
- data science / BI ;
- architecture / cloud data ;
- titres de postes frequents en entreprise francaise ;
- outils / stack ;
- une passe dediee alternance via `typeContrat=E1`.
