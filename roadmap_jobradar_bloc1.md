# Roadmap â€” JobRadar IA
## Pipeline de donnÃ©es sur les offres d'emploi en Intelligence Artificielle
### Bloc 1 â€” CompÃ©tences C1 Ã  C5

---

## Architecture du dÃ©pÃ´t Git

```
jobrador-ia/
â”‚
â”œâ”€â”€ docs/                          # Documentation â€” C4, C5
â”‚   â”œâ”€â”€ merise/
â”‚   â”‚   â”œâ”€â”€ MCD.png                # ModÃ¨le Conceptuel des DonnÃ©es (draw.io)
â”‚   â”‚   â””â”€â”€ MPD.png                # ModÃ¨le Physique des DonnÃ©es
â”‚   â”œâ”€â”€ rgpd_registre.md           # Registre des traitements RGPD
â”‚   â”œâ”€â”€ installation.md            # ProcÃ©dure d'installation complÃ¨te
â”‚   â”œâ”€â”€ api_doc.md                 # Documentation endpoints API
â”‚   â””â”€â”€ matrice_preuves.md         # Tableau C1â†’C5 / preuve / fichier Git / slide
â”‚
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ raw/                       # DonnÃ©es brutes collectÃ©es (ignorÃ©es par Git)
â”‚   â”‚   â””â”€â”€ raw_YYYYMMDD_HHMMSS.json
â”‚   â”œâ”€â”€ processed/                 # Dataset nettoyÃ© final (ignorÃ© par Git)
â”‚   â”‚   â””â”€â”€ clean_dataset.csv
â”‚   â””â”€â”€ fallback/                  # DonnÃ©es statiques de secours â€” OBLIGATOIRE
â”‚       â”œâ”€â”€ fallback_wttj.csv      # 100 offres Welcome to the Jungle
â”‚       â”œâ”€â”€ rome_codes.csv         # Nomenclature ROME officielle
â”‚       â””â”€â”€ hive_agregats.csv      # AgrÃ©gats simulÃ©s si Hive offline
â”‚
â”œâ”€â”€ src/                           # Code source principal
â”‚   â”‚
â”‚   â”œâ”€â”€ collect/                   # C1 â€” Extraction multi-sources
â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”œâ”€â”€ collect.py             # Point d'entrÃ©e â€” orchestre les 5 sources
â”‚   â”‚   â””â”€â”€ fonctions/
â”‚   â”‚       â”œâ”€â”€ __init__.py
â”‚   â”‚       â”œâ”€â”€ collect_offres_france_travail.py  # Source 1 : API REST France Travail
â”‚   â”‚       â”œâ”€â”€ collect_offres_welcome_to_the_jungle.py    # Source 2 : Scraping Welcome to the Jungle
â”‚   â”‚       â”œâ”€â”€ collect_reference_rome.py        # Source 3 : Fichier CSV ROME data.gouv.fr
â”‚   â”‚       â”œâ”€â”€ collect_offres_postgresql_history.py      # Source 4 : PostgreSQL historique
â”‚   â”‚       â””â”€â”€ collect_aggregates_hive.py   # Source 5 : Big Data Hive
â”‚   â”‚
â”‚   â”œâ”€â”€ transform/                 # C3 â€” Nettoyage, normalisation, agrÃ©gation
â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”œâ”€â”€ nettoyage/
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ etape_1_filtrage.py       # Retire les lignes brutes invalides
â”‚   â”‚   â”‚   â”œâ”€â”€ etape_2_normalisation.py   # Harmonise dates, salaires, compÃ©tences
â”‚   â”‚   â”‚   â””â”€â”€ etape_3_deduplication.py   # Supprime les doublons entre sources
â”‚   â”‚   â””â”€â”€ aggregate/
â”‚   â”‚       â”œâ”€â”€ __init__.py
â”‚   â”‚       â””â”€â”€ aggregate.py       # Construit le dataset final consolidÃ©
â”‚   â”‚
â”‚   â””â”€â”€ pipeline.py                # Lance la chaÃ®ne complÃ¨te en 1 commande
â”‚
â”œâ”€â”€ database/                      # C4 â€” Base de donnÃ©es
â”‚   â”œâ”€â”€ models.py                  # SchÃ©ma SQLAlchemy
â”‚   â”œâ”€â”€ import_data.py             # Script d'import du dataset nettoyÃ©
â”‚   â””â”€â”€ migrations/
â”‚       â”œâ”€â”€ 001_init.sql           # CrÃ©ation des tables
â”‚       â””â”€â”€ 002_seed_references.sql # DonnÃ©es de rÃ©fÃ©rence (rÃ©gions, types contrat)
â”‚
â”œâ”€â”€ queries/                       # C2 â€” RequÃªtes SQL documentÃ©es
â”‚   â”œâ”€â”€ extraction.sql             # RequÃªtes PostgreSQL (3 minimum)
â”‚   â””â”€â”€ extraction_hive.hql        # RequÃªtes HiveQL (2 minimum)
â”‚
â”œâ”€â”€ api/                           # C5 â€” API REST
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ main.py                    # Application FastAPI
â”‚   â”œâ”€â”€ auth.py                    # JWT authentication
â”‚   â”œâ”€â”€ schemas.py                 # ModÃ¨les Pydantic
â”‚   â””â”€â”€ routes/
â”‚       â”œâ”€â”€ __init__.py
â”‚       â”œâ”€â”€ offres.py              # GET /offres avec filtres
â”‚       â””â”€â”€ stats.py               # GET /stats/competences, salaires, tendances
â”‚
â”œâ”€â”€ tests/                         # Tests d'intÃ©gration API
â”‚   â”œâ”€â”€ __init__.py
â”‚   â””â”€â”€ test_api.py                # Tests pytest tous les endpoints
â”‚
â”œâ”€â”€ reports/                       # Captures pour la soutenance
â”‚   â”œâ”€â”€ captures/
â”‚   â”‚   â”œâ”€â”€ c1_terminal_collect.png
â”‚   â”‚   â”œâ”€â”€ c2_requetes_sql.png
â”‚   â”‚   â”œâ”€â”€ c3_avant_apres_nettoyage.png
â”‚   â”‚   â”œâ”€â”€ c4_merise_bdd.png
â”‚   â”‚   â””â”€â”€ c5_swagger_api.png
â”‚   â””â”€â”€ phrases_defense.md         # 1 phrase de dÃ©fense par compÃ©tence
â”‚
â”œâ”€â”€ .env.example                   # Variables d'environnement (template)
â”œâ”€â”€ .gitignore
â”œâ”€â”€ docker-compose.yml             # PostgreSQL + Hive
â”œâ”€â”€ requirements.txt
â””â”€â”€ README.md
```

---

## Mise a jour architecture C3

La structure actuellement retenue pour la competence C3 remplace l'ancienne
idee trop floue basee uniquement sur `src/aggregate/`.

La nouvelle organisation est :

```text
src/transform/
  __init__.py
  nettoyage/
    __init__.py
    etape_1_filtrage.py
    etape_2_normalisation.py
    etape_3_deduplication.py
  aggregate/
    __init__.py
    aggregate.py
```

Repartition des roles :
- `nettoyage/etape_1_filtrage.py` : retire les lignes brutes invalides ou inutilisables
- `nettoyage/etape_2_normalisation.py` : harmonise les dates, salaires, competences et champs utiles
- `nettoyage/etape_3_deduplication.py` : retire les doublons entre sources comparables
- `aggregate/aggregate.py` : orchestre toute la transformation et construit le dataset final

Convention actuelle pour C3 :
- chemin de reference du code C3 : `src/transform/`
- point d'entree d'agregation : `src/transform/aggregate/aggregate.py`
- sortie finale attendue : `data/processed/clean_dataset.csv`

## Stack technique

```
Langage         : Python 3.11
API Framework   : FastAPI + Uvicorn
Base de donnÃ©es : PostgreSQL 15
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
# .env.example â€” copier vers .env et remplir

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

# API sÃ©curitÃ©
SECRET_KEY=change-me-32-chars-minimum
```

---

## ModÃ¨le de donnÃ©es â€” MCD Merise

```
EntitÃ©s et relations :

OFFRE (id, titre, description, date_publication,
       salaire_min, salaire_max, type_contrat, statut, source)
    |
    â”œâ”€â”€ publiÃ©e-par â”€â”€â†’ ENTREPRISE (id, nom, secteur, taille)
    |
    â”œâ”€â”€ localisÃ©e-dans â”€â”€â†’ LOCALISATION (id, ville, departement,
    |                                    region, code_postal)
    |
    â””â”€â”€ requiert â”€â”€â†’ COMPETENCE (id, nom, categorie)
                     [table liaison OFFRE_COMPETENCE]
```

### Ce que tu dessines dans draw.io
- Rectangles = entitÃ©s
- Ovales = attributs
- Losanges = relations
- CardinalitÃ©s : une OFFRE requiert 0..n COMPETENCES
                 une COMPETENCE apparaÃ®t dans 0..n OFFRES

---

## MPD PostgreSQL â€” Tables SQL

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

-- Index pour les performances des requÃªtes frÃ©quentes
CREATE INDEX idx_offres_date       ON offres(date_publication);
CREATE INDEX idx_offres_contrat    ON offres(type_contrat);
CREATE INDEX idx_offres_source     ON offres(source);
CREATE INDEX idx_comp_nom          ON competences(nom);
```

---

## Les 5 sources â€” Ce que chaque fichier fait

### Source 1 : src/collect/fonctions/collect_offres_france_travail.py
```
RÃ´le    : Appel API REST France Travail
DonnÃ©es : offres d'emploi structurÃ©es avec salaires
URL     : https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search
Auth    : OAuth2 client_credentials (token renouvelÃ© automatiquement)
ParamÃ¨tres clÃ©s :
  - motsCles = "intelligence artificielle" OR "data engineer"
  - typeContrat = "E1" (alternance) ou vide (tout)
  - departement = optionnel
Retourne : list[dict] normalisÃ©s
Fallback : liste vide + log ERROR (l'API est fiable, pas besoin de CSV)
```

### Source 2 : src/collect/fonctions/collect_offres_welcome_to_the_jungle.py
```
RÃ´le    : Scraping Welcome to the Jungle
DonnÃ©es : offres startups avec stack technique dÃ©taillÃ©e
URL     : https://www.welcometothejungle.com/fr/jobs?query=data+engineer
MÃ©thode : requests + BeautifulSoup, sÃ©lecteurs CSS sur les cards d'offres
Fallback : data/fallback/fallback_wttj.csv â€” 100 offres statiques
           OBLIGATOIRE pour la dÃ©mo hors internet
```

### Source 3 : src/collect/fonctions/collect_reference_rome.py
```
RÃ´le    : Lecture fichier CSV ROME
DonnÃ©es : nomenclature officielle des mÃ©tiers (codes, familles, compÃ©tences)
Fichier : data/fallback/rome_codes.csv
          TÃ©lÃ©chargeable sur : https://www.data.gouv.fr/fr/datasets/
          fichier-rome-des-metiers/
UtilitÃ© : enrichir les offres avec la catÃ©gorie officielle du mÃ©tier
```

### Source 4 : src/collect/fonctions/collect_offres_postgresql_history.py
```
RÃ´le    : Extraction depuis PostgreSQL
DonnÃ©es : offres collectÃ©es lors des runs prÃ©cÃ©dents
RequÃªte : SELECT * FROM offres WHERE date_publication >= NOW() - INTERVAL '30 days'
UtilitÃ© : Ã©viter de recollecter des offres dÃ©jÃ  connues (dÃ©duplication)
Fallback : si table vide (premier run), crÃ©er 20 entrÃ©es de dÃ©monstration
```

### Source 5 : src/collect/fonctions/collect_aggregates_hive.py
```
RÃ´le    : Extraction Big Data Hive
DonnÃ©es : agrÃ©gats prÃ©-calculÃ©s (top compÃ©tences, volumes par rÃ©gion)
RequÃªte : SELECT competence, COUNT(*) as nb, region
          FROM offres_historique
          GROUP BY competence, region
Fallback : data/fallback/hive_agregats.csv si Hive offline
           Ce CSV contient des donnÃ©es prÃ©-calculÃ©es rÃ©alistes
```

---

## Flux de donnÃ©es â€” Ce qui se passe quand tu lances pipeline.py

```
python src/pipeline.py

    Ã‰TAPE 1 â€” Collecte [C1]
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚ collect_offres_france_travail.py  â†’ 200 offres     â”‚
    â”‚ collect_offres_welcome_to_the_jungle.py    â†’ 80 offres      â”‚
    â”‚ collect_reference_rome.py        â†’ 500 codes ROME â”‚
    â”‚ collect_offres_postgresql_history.py      â†’ 150 offres     â”‚
    â”‚ collect_aggregates_hive.py   â†’ 50 agrÃ©gats    â”‚
    â”‚                                     â”‚
    â”‚ â†’ Sauvegarde : data/raw/raw_XXX.jsonâ”‚
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                    â†“
    Ã‰TAPE 2 â€” Nettoyage [C3]
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚ Suppression des doublons (mÃªme URL) â”‚
    â”‚ Normalisation des salaires â†’ entier â”‚
    â”‚ Normalisation des dates â†’ ISO 8601  â”‚
    â”‚ Normalisation des compÃ©tences       â”‚
    â”‚ Suppression des offres corrompues   â”‚
    â”‚                                     â”‚
    â”‚ â†’ Sauvegarde : data/processed/      â”‚
    â”‚   clean_dataset.csv                 â”‚
    â”‚   Avant : 980 entrÃ©es               â”‚
    â”‚   AprÃ¨s  : 743 entrÃ©es propres      â”‚
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                    â†“
    Ã‰TAPE 3 â€” Import base [C4]
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚ Lecture clean_dataset.csv           â”‚
    â”‚ INSERT INTO offres ...              â”‚
    â”‚ INSERT INTO competences ...         â”‚
    â”‚ INSERT INTO offres_competences ...  â”‚
    â”‚                                     â”‚
    â”‚ â†’ PostgreSQL : 743 offres insÃ©rÃ©es  â”‚
    â”‚   RÃ©sultat : 12 tables peuplÃ©es     â”‚
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                    â†“
    Ã‰TAPE 4 â€” API disponible [C5]
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚ uvicorn api.main:app --port 8000    â”‚
    â”‚                                     â”‚
    â”‚ GET /offres?type_contrat=alternance â”‚
    â”‚ GET /stats/competences              â”‚
    â”‚ GET /stats/salaires?region=idf      â”‚
    â”‚ Documentation : /docs (Swagger)     â”‚
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## RequÃªtes SQL â€” Ce que chaque requÃªte prouve [C2]

```sql
-- queries/extraction.sql

-- REQUÃŠTE 1 : Top compÃ©tences demandÃ©es en alternance
-- Objectif : identifier les skills les plus recherchÃ©s
-- Jointures : offres â†’ offres_competences â†’ competences
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

-- REQUÃŠTE 2 : Salaires mÃ©dians par rÃ©gion
-- Objectif : cartographie salariale nationale
-- Filtre : offres avec salaire renseignÃ© uniquement
-- Optimisation : NULLIF pour Ã©viter les salaires Ã  0

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

-- REQUÃŠTE 3 : Ã‰volution hebdomadaire des offres sur 12 semaines
-- Objectif : dÃ©tecter les tendances du marchÃ©
-- Optimisation : DATE_TRUNC Ã©vite un GROUP BY par jour (trop granulaire)

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

## Endpoints API â€” Ce que chaque route expose [C5]

```
POST  /token
      â†’ Authentification, retourne JWT
      â†’ Proof C5 : auth obligatoire

GET   /offres
      â†’ ParamÃ¨tres : competence, region, type_contrat, date_debut, date_fin
      â†’ Retourne : list[OffreOut]
      â†’ Auth : Bearer JWT requis

GET   /offres/{id}
      â†’ DÃ©tail d'une offre avec ses compÃ©tences
      â†’ Auth : Bearer JWT requis

GET   /stats/competences
      â†’ Top 20 compÃ©tences + nb offres + salaire moyen
      â†’ Auth : Bearer JWT requis

GET   /stats/salaires
      â†’ Salaires mÃ©dians par rÃ©gion et type de contrat
      â†’ Auth : Bearer JWT requis

GET   /stats/tendances
      â†’ Ã‰volution hebdomadaire sur 12 semaines
      â†’ Auth : Bearer JWT requis

GET   /health
      â†’ SantÃ© de l'API â€” PAS d'auth (monitoring)
```

---

## Matrice de preuves â€” Ã€ remplir au fur et Ã  mesure

```markdown
# docs/matrice_preuves.md

| CompÃ©tence | Ce que j'ai fait | Fichier Git | Preuve visuelle | Slide |
|---|---|---|---|---|
| C1 | Extraction depuis 5 sources hÃ©tÃ©rogÃ¨nes | src/collect/ | capture terminal collect.py | 4 |
| C2 | 3 requÃªtes SQL documentÃ©es avec justifications | queries/extraction.sql | capture rÃ©sultat requÃªte | 5 |
| C3 | Nettoyage : 980 â†’ 743 entrÃ©es, normalisation salaires/dates/skills | src/transform/ | tableau avant/aprÃ¨s | 6 |
| C4 | MCD+MPD Merise, PostgreSQL, import, registre RGPD | database/ + docs/merise/ | schÃ©ma MCD + pgAdmin | 7 |
| C5 | API FastAPI, JWT, OpenAPI, 6 endpoints, tests pytest verts | api/ + tests/ | capture Swagger + pytest | 8 |
```

---

## Phrases de dÃ©fense â€” Ã€ apprendre avant la soutenance

```markdown
# reports/phrases_defense.md

C1 :
"Ce script prouve que j'automatise la collecte depuis 5 sources
hÃ©tÃ©rogÃ¨nes â€” API REST, scraping, fichier CSV, base de donnÃ©es
et systÃ¨me big data â€” avec gestion des erreurs et fallback,
conformÃ©ment au critÃ¨re C1."

C2 :
"Ces 3 requÃªtes SQL documentÃ©es extraient les donnÃ©es analytiques
clÃ©s : top compÃ©tences, salaires mÃ©dians par rÃ©gion, tendances
hebdomadaires. Chaque jointure et filtre est justifiÃ© en commentaire,
conformÃ©ment au critÃ¨re C2."

C3 :
"Le script d'agrÃ©gation fusionne les 5 sources, supprime les 237
entrÃ©es corrompues, normalise les formats de dates, salaires et
compÃ©tences pour produire un dataset homogÃ¨ne de 743 offres,
conformÃ©ment au critÃ¨re C3."

C4 :
"La base PostgreSQL est modÃ©lisÃ©e selon la mÃ©thode Merise (MCD + MPD),
conforme au RGPD avec un registre des traitements rÃ©digÃ©. Le script
d'import insÃ¨re les donnÃ©es sans erreur, conformÃ©ment au critÃ¨re C4."

C5 :
"L'API REST FastAPI expose les donnÃ©es via 6 endpoints sÃ©curisÃ©s
par JWT, documentÃ©s OpenAPI et couverts par 8 tests pytest qui
passent tous au vert, conformÃ©ment au critÃ¨re C5."
```

---

## Checklist â€” Avant de dire que le projet est terminÃ©

### Code
- [ ] `docker compose up -d` dÃ©marre sans erreur
- [ ] `psql` exÃ©cute `001_init.sql` sans erreur
- [ ] `python src/collect/collect.py` collecte depuis les 5 sources
- [ ] `python src/collect/collect.py --demo` fonctionne HORS INTERNET
- [ ] `python src/transform/aggregate/aggregate.py` produit `clean_dataset.csv`
- [ ] `python database/import_data.py` insÃ¨re sans erreur
- [ ] `uvicorn api.main:app` dÃ©marre sur port 8000
- [ ] `http://localhost:8000/docs` affiche Swagger complet
- [ ] `pytest tests/ -v` tous les tests passent au vert

### Documentation
- [ ] MCD dessinÃ© dans draw.io, exportÃ© en PNG dans `docs/merise/`
- [ ] MPD SQL commentÃ© dans `001_init.sql`
- [ ] `docs/rgpd_registre.md` rÃ©digÃ© avec procÃ©dures de tri
- [ ] `docs/installation.md` reproductible par quelqu'un d'autre
- [ ] `docs/matrice_preuves.md` complÃ©tÃ© pour C1 Ã  C5

### Soutenance
- [ ] 5 captures PNG dans `reports/captures/`
- [ ] `reports/phrases_defense.md` rÃ©digÃ©
- [ ] DÃ©mo testÃ©e entiÃ¨rement hors internet avec `--demo`
- [ ] Tu peux expliquer chaque fonction de chaque fichier en 1 phrase

---

## Ordre de construction recommandÃ©

```
JOUR 1
  1. CrÃ©er le dÃ©pÃ´t Git + structure des dossiers
  2. docker-compose.yml + docker compose up -d
  3. 001_init.sql â†’ crÃ©er les tables
  4. .env Ã  partir de .env.example
  5. Inscription France Travail API (faire Ã§a en premier car dÃ©lai)
  6. Ã‰crire collect_reference_rome.py + collect_offres_postgresql_history.py (les plus simples)
  7. Tester chaque source isolÃ©ment

JOUR 2
  8. collect_offres_france_travail.py (API REST)
  9. collect_offres_welcome_to_the_jungle.py (scraping)
  10. collect_aggregates_hive.py (big data)
  11. collect.py (point d'entrÃ©e, orchestration des 5)
  12. VÃ©rifier que raw_XXX.json est produit

JOUR 3
  13. etape_1_filtrage.py + etape_2_normalisation.py + etape_3_deduplication.py + aggregate.py
  14. import_data.py (insertion PostgreSQL)
  15. queries/extraction.sql (3 requÃªtes documentÃ©es)
  16. pipeline.py (chaÃ®ne complÃ¨te en 1 commande)

JOUR 4
  17. api/auth.py + api/schemas.py
  18. api/routes/offres.py
  19. api/routes/stats.py
  20. api/main.py
  21. tests/test_api.py

JOUR 5
  22. MCD + MPD dans draw.io â†’ export PNG
  23. docs/rgpd_registre.md
  24. docs/matrice_preuves.md
  25. reports/captures/ â†’ prendre toutes les captures
  26. reports/phrases_defense.md
  27. README.md
  28. Test dÃ©mo complÃ¨te hors internet
```

