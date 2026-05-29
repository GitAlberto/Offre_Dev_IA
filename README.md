# JobRadar IA

Cette racine contient le socle du projet de radar d'offres d'emploi IA.

On y trouvera :
- le code source du pipeline ;
- les donnees brutes et nettoyees ;
- la base et les migrations ;
- l'API FastAPI ;
- les tests ;
- la documentation et les supports de soutenance.

## Fichiers racine

- `.env.example` : template des variables d'environnement pour PostgreSQL, Hive, Hue, France Travail et l'API.
- `requirements.txt` : dependances Python minimales du projet.
- `docker-compose.yml` : socle Docker pour PostgreSQL, Hive et Hue.
- `.gitignore` : ignore les secrets, caches Python et sorties generees.
- `roadmap_jobradar_bloc1.md` : feuille de route du projet.

## Etat actuel

Le depot est volontairement en phase de squelette :
- l'arborescence des dossiers est en place ;
- chaque dossier contient un `README.md` explicatif ;
- les fichiers racine minimaux sont prets ;
- le code metier sera ajoute et teste pas a pas.
- l'infrastructure Hive + Hue est maintenant preparee pour la suite Big Data.

## Prochaine etape

Les prochaines briques logiques a creer sont :
- les fichiers Python vides de collecte, d'agregation et d'API ;
- les scripts SQL de migration ;
- les premiers fichiers de donnees de fallback.
