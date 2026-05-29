# Requetes Hive

Ce dossier contient les requetes HiveQL du projet.

Il sert a :
- stocker les requetes analytiques executees dans Hive ;
- versionner les preuves de travail Big Data ;
- eviter d'enfouir les requetes directement dans le code Python.

Le premier fichier a garder a jour est :
- `extraction_hive.hql` : requete d'agregation lue par `collect_aggregates_hive.py`.
