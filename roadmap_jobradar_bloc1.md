# Roadmap — JobRadar IA
## Pipeline de données sur les offres d'emploi en Intelligence Artificielle
### Bloc 1 — Compétences C1 à C5

---

## Architecture du dépôt Git

```
jobrador-ia/
│
├── docs/                          # Documentation — C4, C5
│   ├── merise/
│   │   ├── MCD.png                # Modèle Conceptuel des Données (draw.io)
│   │   └── MPD.png                # Modèle Physique des Données
│   ├── rgpd_registre.md           # Registre des traitements RGPD
│   ├── installation.md            # Procédure d'installation complète
│   ├── api_doc.md                 # Documentation endpoints API
│   └── matrice_preuves.md         # Tableau C1→C5 / preuve / fichier Git / slide
│
├── data/
│   ├── raw/                       # Données brutes collectées (ignorées par Git)
│   │   └── raw_YYYYMMDD_HHMMSS.json
│   ├── processed/                 # Dataset nettoyé final (ignoré par Git)
│   │   └── clean_dataset.csv
│   └── fallback/                  # Données statiques de secours — OBLIGATOIRE
│       ├── fallback_wttj.csv      # 100 offres Welcome to the Jungle
│       ├── rome_codes.csv         # Nomenclature ROME officielle
│       └── hive_agregats.csv      # Agrégats simulés si Hive offline
│
├── src/                           # Code source principal
│   │
│   ├── collect/                   # C1 — Extraction multi-sources
│   │   ├── __init__.py
│   │   ├── collect.py             # Point d'entrée — orchestre les 5 sources
│   │   └── sources/
│   │       ├── __init__.py
│   │       ├── france_travail.py  # Source 1 : API REST France Travail
│   │       ├── wttj_scraper.py    # Source 2 : Scraping Welcome to the Jungle
│   │       ├── rome_csv.py        # Source 3 : Fichier CSV ROME data.gouv.fr
│   │       ├── pg_history.py      # Source 4 : PostgreSQL historique
│   │       └── hive_agregats.py   # Source 5 : Big Data Hive
│   │
│   ├── aggregate/                 # C3 — Nettoyage et normalisation
│   │   ├── __init__.py
│   │   └── aggregate.py           # Fusion, nettoyage, normalisation
│   │
│   └── pipeline.py                # Lance la chaîne complète en 1 commande
│
├── database/                      # C4 — Base de données
│   ├── models.py                  # Schéma SQLAlchemy
│   ├── import_data.py             # Script d'import du dataset nettoyé
│   └── migrations/
│       ├── 001_init.sql           # Création des tables
│       └── 002_seed_references.sql # Données de référence (régions, types contrat)
│
├── queries/                       # C2 — Requêtes SQL documentées
│   ├── extraction.sql             # Requêtes PostgreSQL (3 minimum)
│   └── extraction_hive.hql        # Requêtes HiveQL (2 minimum)
│
├── api/                           # C5 — API REST
│   ├── __init__.py
│   ├── main.py                    # Application FastAPI
│   ├── auth.py                    # JWT authentication
│   ├── schemas.py                 # Modèles Pydantic
│   └── routes/
│       ├── __init__.py
│       ├── offres.py              # GET /offres avec filtres
│       └── stats.py               # GET /stats/competences, salaires, tendances
│
├── tests/                         # Tests d'intégration API
│   ├── __init__.py
│   └── test_api.py                # Tests pytest tous les endpoints
│
├── reports/                       # Captures pour la soutenance
│   ├── captures/
│   │   ├── c1_terminal_collect.png
│   │   ├── c2_requetes_sql.png
│   │   ├── c3_avant_apres_nettoyage.png
│   │   ├── c4_merise_bdd.png
│   │   └── c5_swagger_api.png
│   └── phrases_defense.md         # 1 phrase de défense par compétence
│
├── .env.example                   # Variables d'environnement (template)
├── .gitignore
├── docker-compose.yml             # PostgreSQL + Hive
├── requirements.txt
└── README.md
```

---

## Stack technique

```
Langage         : Python 3.11
API Framework   : FastAPI + Uvicorn
Base de données : PostgreSQL 15
Big Data        : Apache Hive 3 (Docker)
ORM             : SQLAlchemy
Auth            : JWT (python-jose)
Tests           : pytest + httpx
Scraping        : requests + BeautifulSoup4
Data            : pandas
Versionning     : Git + GitHub
```

---

## Services Docker

```yaml
# docker-compose.yml
services:

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: jobradar
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  hive:
    image: apache/hive:3.1.3
    ports:
      - "10000:10000"   # HiveServer2
      - "10002:10002"   # Web UI
    environment:
      SERVICE_NAME: hiveserver2

volumes:
  pgdata:
```

---

## Variables d'environnement

```bash
# .env.example — copier vers .env et remplir

# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_DB=jobradar
PG_USER=admin
PG_PASSWORD=secret
DATABASE_URL=postgresql://admin:secret@localhost/jobradar

# Hive
HIVE_HOST=localhost
HIVE_PORT=10000

# France Travail API
# Inscription sur : https://francetravail.io/data/api
FRANCE_TRAVAIL_CLIENT_ID=
FRANCE_TRAVAIL_CLIENT_SECRET=

# API sécurité
SECRET_KEY=change-me-32-chars-minimum
```

---

## Modèle de données — MCD Merise

```
Entités et relations :

OFFRE (id, titre, description, date_publication,
       salaire_min, salaire_max, type_contrat, statut, source)
    |
    ├── publiée-par ──→ ENTREPRISE (id, nom, secteur, taille)
    |
    ├── localisée-dans ──→ LOCALISATION (id, ville, departement,
    |                                    region, code_postal)
    |
    └── requiert ──→ COMPETENCE (id, nom, categorie)
                     [table liaison OFFRE_COMPETENCE]
```

### Ce que tu dessines dans draw.io
- Rectangles = entités
- Ovales = attributs
- Losanges = relations
- Cardinalités : une OFFRE requiert 0..n COMPETENCES
                 une COMPETENCE apparaît dans 0..n OFFRES

---

## MPD PostgreSQL — Tables SQL

```sql
-- database/migrations/001_init.sql

CREATE TABLE entreprises (
    id          SERIAL PRIMARY KEY,
    nom         VARCHAR(200) NOT NULL,
    secteur     VARCHAR(100),
    taille      VARCHAR(50)
);

CREATE TABLE localisations (
    id           SERIAL PRIMARY KEY,
    ville        VARCHAR(100),
    departement  VARCHAR(100),
    region       VARCHAR(100),
    code_postal  VARCHAR(10)
);

CREATE TABLE competences (
    id        SERIAL PRIMARY KEY,
    nom       VARCHAR(100) UNIQUE NOT NULL,
    categorie VARCHAR(50)  -- 'langage', 'outil', 'cloud', 'methode'
);

CREATE TABLE offres (
    id               SERIAL PRIMARY KEY,
    titre            VARCHAR(300) NOT NULL,
    description      TEXT,
    date_publication DATE,
    salaire_min      INTEGER,
    salaire_max      INTEGER,
    type_contrat     VARCHAR(50), -- 'CDI', 'CDD', 'Alternance', 'Stage'
    statut           VARCHAR(20) DEFAULT 'active',
    source           VARCHAR(50),
    entreprise_id    INTEGER REFERENCES entreprises(id),
    localisation_id  INTEGER REFERENCES localisations(id),
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE offres_competences (
    offre_id      INTEGER REFERENCES offres(id),
    competence_id INTEGER REFERENCES competences(id),
    PRIMARY KEY (offre_id, competence_id)
);

-- Index pour les performances des requêtes fréquentes
CREATE INDEX idx_offres_date       ON offres(date_publication);
CREATE INDEX idx_offres_contrat    ON offres(type_contrat);
CREATE INDEX idx_offres_source     ON offres(source);
CREATE INDEX idx_comp_nom          ON competences(nom);
```

---

## Les 5 sources — Ce que chaque fichier fait

### Source 1 : src/collect/sources/france_travail.py
```
Rôle    : Appel API REST France Travail
Données : offres d'emploi structurées avec salaires
URL     : https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search
Auth    : OAuth2 client_credentials (token renouvelé automatiquement)
Paramètres clés :
  - motsCles = "intelligence artificielle" OR "data engineer"
  - typeContrat = "E1" (alternance) ou vide (tout)
  - departement = optionnel
Retourne : list[dict] normalisés
Fallback : liste vide + log ERROR (l'API est fiable, pas besoin de CSV)
```

### Source 2 : src/collect/sources/wttj_scraper.py
```
Rôle    : Scraping Welcome to the Jungle
Données : offres startups avec stack technique détaillée
URL     : https://www.welcometothejungle.com/fr/jobs?query=data+engineer
Méthode : requests + BeautifulSoup, sélecteurs CSS sur les cards d'offres
Fallback : data/fallback/fallback_wttj.csv — 100 offres statiques
           OBLIGATOIRE pour la démo hors internet
```

### Source 3 : src/collect/sources/rome_csv.py
```
Rôle    : Lecture fichier CSV ROME
Données : nomenclature officielle des métiers (codes, familles, compétences)
Fichier : data/fallback/rome_codes.csv
          Téléchargeable sur : https://www.data.gouv.fr/fr/datasets/
          fichier-rome-des-metiers/
Utilité : enrichir les offres avec la catégorie officielle du métier
```

### Source 4 : src/collect/sources/pg_history.py
```
Rôle    : Extraction depuis PostgreSQL
Données : offres collectées lors des runs précédents
Requête : SELECT * FROM offres WHERE date_publication >= NOW() - INTERVAL '30 days'
Utilité : éviter de recollecter des offres déjà connues (déduplication)
Fallback : si table vide (premier run), créer 20 entrées de démonstration
```

### Source 5 : src/collect/sources/hive_agregats.py
```
Rôle    : Extraction Big Data Hive
Données : agrégats pré-calculés (top compétences, volumes par région)
Requête : SELECT competence, COUNT(*) as nb, region
          FROM offres_historique
          GROUP BY competence, region
Fallback : data/fallback/hive_agregats.csv si Hive offline
           Ce CSV contient des données pré-calculées réalistes
```

---

## Flux de données — Ce qui se passe quand tu lances pipeline.py

```
python src/pipeline.py

    ÉTAPE 1 — Collecte [C1]
    ┌─────────────────────────────────────┐
    │ france_travail.py  → 200 offres     │
    │ wttj_scraper.py    → 80 offres      │
    │ rome_csv.py        → 500 codes ROME │
    │ pg_history.py      → 150 offres     │
    │ hive_agregats.py   → 50 agrégats    │
    │                                     │
    │ → Sauvegarde : data/raw/raw_XXX.json│
    └─────────────────────────────────────┘
                    ↓
    ÉTAPE 2 — Nettoyage [C3]
    ┌─────────────────────────────────────┐
    │ Suppression des doublons (même URL) │
    │ Normalisation des salaires → entier │
    │ Normalisation des dates → ISO 8601  │
    │ Normalisation des compétences       │
    │ Suppression des offres corrompues   │
    │                                     │
    │ → Sauvegarde : data/processed/      │
    │   clean_dataset.csv                 │
    │   Avant : 980 entrées               │
    │   Après  : 743 entrées propres      │
    └─────────────────────────────────────┘
                    ↓
    ÉTAPE 3 — Import base [C4]
    ┌─────────────────────────────────────┐
    │ Lecture clean_dataset.csv           │
    │ INSERT INTO offres ...              │
    │ INSERT INTO competences ...         │
    │ INSERT INTO offres_competences ...  │
    │                                     │
    │ → PostgreSQL : 743 offres insérées  │
    │   Résultat : 12 tables peuplées     │
    └─────────────────────────────────────┘
                    ↓
    ÉTAPE 4 — API disponible [C5]
    ┌─────────────────────────────────────┐
    │ uvicorn api.main:app --port 8000    │
    │                                     │
    │ GET /offres?type_contrat=alternance │
    │ GET /stats/competences              │
    │ GET /stats/salaires?region=idf      │
    │ Documentation : /docs (Swagger)     │
    └─────────────────────────────────────┘
```

---

## Requêtes SQL — Ce que chaque requête prouve [C2]

```sql
-- queries/extraction.sql

-- REQUÊTE 1 : Top compétences demandées en alternance
-- Objectif : identifier les skills les plus recherchés
-- Jointures : offres → offres_competences → competences
-- Filtre : type_contrat alternance, 90 derniers jours
-- Optimisation : INDEX sur type_contrat et date_publication

SELECT
    c.nom                    AS competence,
    c.categorie,
    COUNT(DISTINCT o.id)     AS nb_offres,
    ROUND(AVG(o.salaire_min)) AS salaire_moyen_min
FROM offres o
JOIN offres_competences oc ON o.id = oc.offre_id
JOIN competences c         ON c.id = oc.competence_id
WHERE o.type_contrat = 'Alternance'
  AND o.date_publication >= NOW() - INTERVAL '90 days'
GROUP BY c.nom, c.categorie
ORDER BY nb_offres DESC
LIMIT 20;

-- REQUÊTE 2 : Salaires médians par région
-- Objectif : cartographie salariale nationale
-- Filtre : offres avec salaire renseigné uniquement
-- Optimisation : NULLIF pour éviter les salaires à 0

SELECT
    l.region,
    COUNT(o.id)                              AS nb_offres,
    PERCENTILE_CONT(0.5) WITHIN GROUP
        (ORDER BY o.salaire_min)             AS salaire_median,
    MIN(o.salaire_min)                       AS salaire_min,
    MAX(o.salaire_max)                       AS salaire_max
FROM offres o
JOIN localisations l ON o.localisation_id = l.id
WHERE o.salaire_min IS NOT NULL
  AND o.salaire_min > 0
GROUP BY l.region
ORDER BY salaire_median DESC;

-- REQUÊTE 3 : Évolution hebdomadaire des offres sur 12 semaines
-- Objectif : détecter les tendances du marché
-- Optimisation : DATE_TRUNC évite un GROUP BY par jour (trop granulaire)

SELECT
    DATE_TRUNC('week', date_publication)  AS semaine,
    type_contrat,
    COUNT(*)                              AS nb_offres
FROM offres
WHERE date_publication >= NOW() - INTERVAL '12 weeks'
GROUP BY DATE_TRUNC('week', date_publication), type_contrat
ORDER BY semaine ASC, type_contrat;
```

---

## Endpoints API — Ce que chaque route expose [C5]

```
POST  /token
      → Authentification, retourne JWT
      → Proof C5 : auth obligatoire

GET   /offres
      → Paramètres : competence, region, type_contrat, date_debut, date_fin
      → Retourne : list[OffreOut]
      → Auth : Bearer JWT requis

GET   /offres/{id}
      → Détail d'une offre avec ses compétences
      → Auth : Bearer JWT requis

GET   /stats/competences
      → Top 20 compétences + nb offres + salaire moyen
      → Auth : Bearer JWT requis

GET   /stats/salaires
      → Salaires médians par région et type de contrat
      → Auth : Bearer JWT requis

GET   /stats/tendances
      → Évolution hebdomadaire sur 12 semaines
      → Auth : Bearer JWT requis

GET   /health
      → Santé de l'API — PAS d'auth (monitoring)
```

---

## Matrice de preuves — À remplir au fur et à mesure

```markdown
# docs/matrice_preuves.md

| Compétence | Ce que j'ai fait | Fichier Git | Preuve visuelle | Slide |
|---|---|---|---|---|
| C1 | Extraction depuis 5 sources hétérogènes | src/collect/ | capture terminal collect.py | 4 |
| C2 | 3 requêtes SQL documentées avec justifications | queries/extraction.sql | capture résultat requête | 5 |
| C3 | Nettoyage : 980 → 743 entrées, normalisation salaires/dates/skills | src/aggregate/ | tableau avant/après | 6 |
| C4 | MCD+MPD Merise, PostgreSQL, import, registre RGPD | database/ + docs/merise/ | schéma MCD + pgAdmin | 7 |
| C5 | API FastAPI, JWT, OpenAPI, 6 endpoints, tests pytest verts | api/ + tests/ | capture Swagger + pytest | 8 |
```

---

## Phrases de défense — À apprendre avant la soutenance

```markdown
# reports/phrases_defense.md

C1 :
"Ce script prouve que j'automatise la collecte depuis 5 sources
hétérogènes — API REST, scraping, fichier CSV, base de données
et système big data — avec gestion des erreurs et fallback,
conformément au critère C1."

C2 :
"Ces 3 requêtes SQL documentées extraient les données analytiques
clés : top compétences, salaires médians par région, tendances
hebdomadaires. Chaque jointure et filtre est justifié en commentaire,
conformément au critère C2."

C3 :
"Le script d'agrégation fusionne les 5 sources, supprime les 237
entrées corrompues, normalise les formats de dates, salaires et
compétences pour produire un dataset homogène de 743 offres,
conformément au critère C3."

C4 :
"La base PostgreSQL est modélisée selon la méthode Merise (MCD + MPD),
conforme au RGPD avec un registre des traitements rédigé. Le script
d'import insère les données sans erreur, conformément au critère C4."

C5 :
"L'API REST FastAPI expose les données via 6 endpoints sécurisés
par JWT, documentés OpenAPI et couverts par 8 tests pytest qui
passent tous au vert, conformément au critère C5."
```

---

## Checklist — Avant de dire que le projet est terminé

### Code
- [ ] `docker compose up -d` démarre sans erreur
- [ ] `psql` exécute `001_init.sql` sans erreur
- [ ] `python src/collect/collect.py` collecte depuis les 5 sources
- [ ] `python src/collect/collect.py --demo` fonctionne HORS INTERNET
- [ ] `python src/aggregate/aggregate.py` produit `clean_dataset.csv`
- [ ] `python database/import_data.py` insère sans erreur
- [ ] `uvicorn api.main:app` démarre sur port 8000
- [ ] `http://localhost:8000/docs` affiche Swagger complet
- [ ] `pytest tests/ -v` tous les tests passent au vert

### Documentation
- [ ] MCD dessiné dans draw.io, exporté en PNG dans `docs/merise/`
- [ ] MPD SQL commenté dans `001_init.sql`
- [ ] `docs/rgpd_registre.md` rédigé avec procédures de tri
- [ ] `docs/installation.md` reproductible par quelqu'un d'autre
- [ ] `docs/matrice_preuves.md` complété pour C1 à C5

### Soutenance
- [ ] 5 captures PNG dans `reports/captures/`
- [ ] `reports/phrases_defense.md` rédigé
- [ ] Démo testée entièrement hors internet avec `--demo`
- [ ] Tu peux expliquer chaque fonction de chaque fichier en 1 phrase

---

## Ordre de construction recommandé

```
JOUR 1
  1. Créer le dépôt Git + structure des dossiers
  2. docker-compose.yml + docker compose up -d
  3. 001_init.sql → créer les tables
  4. .env à partir de .env.example
  5. Inscription France Travail API (faire ça en premier car délai)
  6. Écrire rome_csv.py + pg_history.py (les plus simples)
  7. Tester chaque source isolément

JOUR 2
  8. france_travail.py (API REST)
  9. wttj_scraper.py (scraping)
  10. hive_agregats.py (big data)
  11. collect.py (point d'entrée, orchestration des 5)
  12. Vérifier que raw_XXX.json est produit

JOUR 3
  13. aggregate.py (nettoyage complet)
  14. import_data.py (insertion PostgreSQL)
  15. queries/extraction.sql (3 requêtes documentées)
  16. pipeline.py (chaîne complète en 1 commande)

JOUR 4
  17. api/auth.py + api/schemas.py
  18. api/routes/offres.py
  19. api/routes/stats.py
  20. api/main.py
  21. tests/test_api.py

JOUR 5
  22. MCD + MPD dans draw.io → export PNG
  23. docs/rgpd_registre.md
  24. docs/matrice_preuves.md
  25. reports/captures/ → prendre toutes les captures
  26. reports/phrases_defense.md
  27. README.md
  28. Test démo complète hors internet
```
