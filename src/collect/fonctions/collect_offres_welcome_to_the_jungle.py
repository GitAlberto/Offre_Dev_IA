"""Module de collecte Welcome to the Jungle.

Ce module utilise prioritairement Selenium pour charger les pages WTTJ, puis
BeautifulSoup pour parser le DOM rendu et extraire les offres d'emploi.

Ce qui est cense appeler ce module :
- `src/collect/collect.py` doit appeler
  `collect_offres_welcome_to_the_jungle()` ;
- `src/pipeline.py` devra passer par l'orchestrateur plutot que par ce module.

Ce que ce module est cense faire :
- construire une URL WTTJ adaptee a une requete metier ;
- charger les pages de resultats avec Selenium ;
- parser les cartes d'offres visibles ;
- mapper chaque offre vers le schema brut du projet ;
- utiliser si besoin un CSV local de secours.

Limite importante :
- ce module collecte et mappe la source WTTJ ;
- le nettoyage, la normalisation et la deduplication restent geres plus loin
  dans le pipeline.
"""

from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as expected
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:  # pragma: no cover - simple repli si Selenium manque
    webdriver = None
    TimeoutException = Exception
    WebDriverException = Exception
    ChromeOptions = None
    By = None
    expected = None
    WebDriverWait = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WTTJ_QUERY = "data engineer"
DEFAULT_WTTJ_QUERY_MODE = "focused"
DEFAULT_WTTJ_BASE_URL = "https://www.welcometothejungle.com"
DEFAULT_WTTJ_JOBS_URL = f"{DEFAULT_WTTJ_BASE_URL}/fr/jobs"
DEFAULT_WTTJ_PAGES_BASE_URL = f"{DEFAULT_WTTJ_BASE_URL}/fr/pages"
DEFAULT_WTTJ_FALLBACK_PATH = PROJECT_ROOT / "data" / "fallback" / "fallback_wttj.csv"
DEFAULT_WTTJ_TIMEOUT_SECONDS = 30
DEFAULT_WTTJ_MAX_PAGES = 10
DEFAULT_WTTJ_PREFLIGHT_TIMEOUT_SECONDS = 10
WTTJ_QUERY_GROUPS_BY_MODE: dict[str, list[str]] = {
    "legacy": [
        "data engineer",
    ],
    "focused": [
        "data engineer",
        "data scientist",
        "data analyst",
        "machine learning engineer",
    ],
    "broad": [
        "data engineer",
        "data scientist",
        "data analyst",
        "machine learning engineer",
        "consultant data",
        "consultant BI",
        "architecte cloud",
        "developpeur big data",
        "alternance data",
        "mlops engineer",
        "ai engineer",
        "data architect",
        "analytics engineer",
        "data platform engineer",
        "cloud data engineer",
        "business intelligence",
        "business analyst data",
        "consultant data",
        "lead data engineer",
    ],
    "max_volume": [
        "data engineer",
        "ingenieur donnees",
        "ingenieur data",
        "data pipeline",
        "ETL developpeur",
        "developpeur ETL",
        "ingenieur ETL",
        "data integration",
        "data scientist",
        "analyste donnees",
        "analyste data",
        "data analyst",
        "business analyst data",
        "machine learning engineer",
        "ingenieur machine learning",
        "ML engineer",
        "mlops engineer",
        "MLOps",
        "ai engineer",
        "developpeur intelligence artificielle",
        "developpeur IA",
        "deep learning",
        "NLP engineer",
        "computer vision engineer",
        "ingenieur NLP",
        "LLM engineer",
        "data architect",
        "architecte data",
        "analytics engineer",
        "data platform engineer",
        "cloud data engineer",
        "ingenieur cloud donnees",
        "architecte cloud",
        "business intelligence",
        "business analyst data",
        "consultant data",
        "consultant BI",
        "consultant decisionnel",
        "lead data engineer",
        "chef de projet data",
        "responsable data",
        "lead data",
        "big data engineer",
        "developpeur big data",
        "ingenieur big data",
        "spark engineer",
        "ingenieur spark",
        "kafka engineer",
        "airflow",
        "dbt developer",
        "developpeur dbt",
        "computer vision engineer",
        "nlp engineer",
        "llm engineer",
        "databricks",
        "snowflake",
        "alternance data",
        "apprentissage data",
        "alternance IA",
        "alternance machine learning",
        "alternance data engineer",
        "stage data",
        "stage IA",
    ],
}
WTTJ_OFFER_LINK_PATTERN = re.compile(
    r"^/fr/companies/[^/]+/jobs/[^/?#]+/?$",
    re.IGNORECASE,
)
WTTJ_PAGE_NUMBER_PATTERN = re.compile(r"[?&]page=(\d+)")


def normalize_wttj_query_for_slug(query: str) -> str:
    """Transformer une requete libre en slug WTTJ pour les pages metier."""

    query_without_accents = unicodedata.normalize("NFKD", query)
    query_without_accents = query_without_accents.encode("ascii", "ignore").decode(
        "ascii"
    )
    query_without_accents = query_without_accents.lower()
    query_without_accents = re.sub(r"[^a-z0-9]+", "-", query_without_accents)
    query_without_accents = re.sub(r"-{2,}", "-", query_without_accents)
    return query_without_accents.strip("-")


def build_wttj_search_url(query: str = DEFAULT_WTTJ_QUERY) -> str:
    """Construire l'URL de recherche WTTJ la plus generique."""

    safe_query = query.strip().replace(" ", "%20")
    return f"{DEFAULT_WTTJ_JOBS_URL}?query={safe_query}"


def build_wttj_metier_page_url(
    query: str = DEFAULT_WTTJ_QUERY,
    page_number: int = 1,
) -> str:
    """Construire l'URL de la page metier WTTJ la plus exploitable pour le scraping."""

    slug = normalize_wttj_query_for_slug(query)
    base_url = f"{DEFAULT_WTTJ_PAGES_BASE_URL}/emploi-{slug}"
    if page_number <= 1:
        return base_url

    return f"{base_url}?page={page_number}"


def get_wttj_timeout_seconds() -> int:
    """Lire le timeout WTTJ depuis l'environnement si present."""

    raw_value = os.getenv("WTTJ_TIMEOUT_SECONDS", str(DEFAULT_WTTJ_TIMEOUT_SECONDS))
    try:
        return max(5, int(raw_value))
    except ValueError:
        return DEFAULT_WTTJ_TIMEOUT_SECONDS


def get_wttj_preflight_timeout_seconds() -> int:
    """Lire le timeout de preverification WTTJ depuis l'environnement si present."""

    raw_value = os.getenv(
        "WTTJ_PREFLIGHT_TIMEOUT_SECONDS",
        str(DEFAULT_WTTJ_PREFLIGHT_TIMEOUT_SECONDS),
    )
    try:
        return max(3, int(raw_value))
    except ValueError:
        return DEFAULT_WTTJ_PREFLIGHT_TIMEOUT_SECONDS


def get_wttj_max_pages() -> int:
    """Lire la limite de pagination WTTJ depuis l'environnement si presente."""

    raw_value = os.getenv("WTTJ_MAX_PAGES", str(DEFAULT_WTTJ_MAX_PAGES))
    try:
        parsed_value = int(raw_value)
    except ValueError:
        return DEFAULT_WTTJ_MAX_PAGES

    if parsed_value <= 0:
        return DEFAULT_WTTJ_MAX_PAGES

    return parsed_value


def get_wttj_query_mode() -> str:
    """Lire le mode de requetes WTTJ depuis l'environnement si present."""

    query_mode = os.getenv("WTTJ_QUERY_MODE", DEFAULT_WTTJ_QUERY_MODE).strip().lower()
    if query_mode not in WTTJ_QUERY_GROUPS_BY_MODE:
        return DEFAULT_WTTJ_QUERY_MODE

    return query_mode


def normaliser_wttj_queries(queries: list[str]) -> list[str]:
    """Nettoyer, dedoublonner et conserver l'ordre des requetes WTTJ."""

    normalized_queries: list[str] = []
    seen_queries: set[str] = set()

    for query in queries:
        normalized_query = query.strip()
        if not normalized_query:
            continue

        dedup_key = normalized_query.casefold()
        if dedup_key in seen_queries:
            continue

        seen_queries.add(dedup_key)
        normalized_queries.append(normalized_query)

    return normalized_queries


def build_wttj_queries(
    query: str | None = None,
    queries: list[str] | None = None,
    query_mode: str | None = None,
) -> list[str]:
    """Construire la liste finale des requetes WTTJ a lancer."""

    if queries:
        return normaliser_wttj_queries(queries)

    if query and query.strip():
        return normaliser_wttj_queries([query])

    selected_query_mode = (query_mode or get_wttj_query_mode()).strip().lower()
    if selected_query_mode not in WTTJ_QUERY_GROUPS_BY_MODE:
        selected_query_mode = DEFAULT_WTTJ_QUERY_MODE

    return normaliser_wttj_queries(WTTJ_QUERY_GROUPS_BY_MODE[selected_query_mode])


def build_wttj_webdriver() -> webdriver.Chrome | None:
    """Construire un navigateur Chrome headless pour WTTJ."""

    if webdriver is None or ChromeOptions is None:
        print(
            "Welcome to the Jungle: Selenium n'est pas installe, scraping live indisponible."
        )
        return None

    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1600,2200")
    options.add_argument("--lang=fr-FR")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")

    chrome_binary = os.getenv("WTTJ_CHROME_BINARY", "").strip()
    if chrome_binary:
        options.binary_location = chrome_binary

    try:
        return webdriver.Chrome(options=options)
    except WebDriverException as error:
        print(
            "Welcome to the Jungle: echec au demarrage du navigateur Selenium : "
            f"{error}"
        )
        return None


def load_wttj_page_html(
    driver: webdriver.Chrome,
    url: str,
    timeout_seconds: int,
) -> str:
    """Charger une page WTTJ avec Selenium et retourner le HTML rendu."""

    driver.get(url)

    if WebDriverWait is not None and expected is not None and By is not None:
        WebDriverWait(driver, timeout_seconds).until(
            expected.presence_of_element_located((By.TAG_NAME, "body"))
        )
        dismiss_wttj_cookie_banner(driver=driver, timeout_seconds=timeout_seconds)
        wait_for_wttj_offer_cards(driver=driver, timeout_seconds=timeout_seconds)

    return driver.page_source


def dismiss_wttj_cookie_banner(
    driver: webdriver.Chrome,
    timeout_seconds: int,
) -> None:
    """Fermer le bandeau cookies WTTJ quand il apparait."""

    if WebDriverWait is None or By is None:
        return

    try:
        WebDriverWait(driver, min(timeout_seconds, 10)).until(
            lambda current_driver: current_driver.find_elements(By.TAG_NAME, "button")
        )
    except TimeoutException:
        return

    for expected_label in ("OK pour moi", "Non merci"):
        for button in driver.find_elements(By.TAG_NAME, "button"):
            if button.text.strip() != expected_label:
                continue

            try:
                driver.execute_script("arguments[0].click();", button)
            except WebDriverException:
                continue
            return


def wait_for_wttj_offer_cards(
    driver: webdriver.Chrome,
    timeout_seconds: int,
) -> None:
    """Attendre que les cartes d'offres WTTJ soient presentes dans le DOM."""

    if WebDriverWait is None or By is None:
        return

    WebDriverWait(driver, timeout_seconds).until(
        lambda current_driver: bool(
            current_driver.find_elements(By.CSS_SELECTOR, "div[data-role='jobs:thumb']")
        )
    )


def is_wttj_offer_href(href: str | None) -> bool:
    """Verifier si un lien ressemble a une fiche d'offre WTTJ."""

    if not href:
        return False

    return bool(WTTJ_OFFER_LINK_PATTERN.match(href))


def extract_wttj_offer_links_from_html(html: str) -> list[str]:
    """Extraire tous les liens d'offres WTTJ visibles dans le HTML rendu."""

    soup = BeautifulSoup(html, "html.parser")
    hrefs: list[str] = []
    seen_hrefs: set[str] = set()

    for link in soup.select("a[href]"):
        href = link.get("href")
        if not is_wttj_offer_href(href):
            continue
        if href in seen_hrefs:
            continue

        seen_hrefs.add(href)
        hrefs.append(href)

    return hrefs


def detect_wttj_last_page_number(html: str) -> int | None:
    """Detecter le dernier numero de page visible dans la pagination WTTJ."""

    soup = BeautifulSoup(html, "html.parser")
    page_numbers: list[int] = []

    for link in soup.select("a[href]"):
        href = link.get("href", "")
        match = WTTJ_PAGE_NUMBER_PATTERN.search(href)
        if not match:
            continue
        page_numbers.append(int(match.group(1)))

    if not page_numbers:
        return None

    return max(page_numbers)


def wttj_html_contains_offer_cards(html: str) -> bool:
    """Verifier rapidement si un HTML WTTJ contient des cartes d'offres."""

    return "data-role=\"jobs:thumb\"" in html and "jobs-results-list" in html


def precheck_wttj_query_support(
    query: str,
    timeout_seconds: int,
) -> tuple[bool, str]:
    """Verifier rapidement si une page metier WTTJ existe vraiment pour une requete."""

    url = build_wttj_metier_page_url(query=query, page_number=1)

    try:
        response = requests.get(
            url,
            timeout=timeout_seconds,
            headers={"User-Agent": "Mozilla/5.0"},
        )
    except requests.RequestException as error:
        print(
            "Welcome to the Jungle: preverification impossible pour "
            f"'{query}' ({error})."
        )
        return True, url

    if response.status_code >= 400:
        print(
            "Welcome to the Jungle: page metier indisponible pour "
            f"'{query}' (status={response.status_code})."
        )
        return False, url

    if not wttj_html_contains_offer_cards(response.text):
        print(
            "Welcome to the Jungle: pas de vraie page d'offres metier pour "
            f"'{query}', requete ignoree."
        )
        return False, url

    return True, url


def extract_wttj_cards_from_html(html: str) -> list[dict[str, Any]]:
    """Extraire des offres WTTJ depuis le HTML rendu."""

    soup = BeautifulSoup(html, "html.parser")
    offer_cards: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for thumb in soup.select("div[data-role='jobs:thumb']"):
        offer_id = thumb.get("data-object-id", "").strip()
        body = thumb.select_one("div > a > h2")
        if body is None:
            continue

        title_tag = body
        title = title_tag.get_text(" ", strip=True)

        title_anchor = title_tag.find_parent("a", href=True)
        if title_anchor is None:
            continue

        href = title_anchor.get("href", "").strip()
        if not is_wttj_offer_href(href):
            continue

        if offer_id and offer_id in seen_ids:
            continue
        if offer_id:
            seen_ids.add(offer_id)

        parent_body = title_anchor.find_parent("div")
        if parent_body is None:
            continue

        company = ""
        description = ""
        published_at = ""
        metadata_texts: list[str] = []

        direct_children = [
            child
            for child in parent_body.find_all(recursive=False)
            if getattr(child, "name", None) is not None
        ]

        if len(direct_children) >= 2:
            company_tag = direct_children[1].select_one("span")
            if company_tag is not None:
                company = company_tag.get_text(" ", strip=True)

        if len(direct_children) >= 3 and direct_children[2].name == "p":
            description = direct_children[2].get_text(" ", strip=True)

        if len(direct_children) >= 4:
            metadata_container = direct_children[3]
            for item in metadata_container.find_all("div", recursive=False):
                item_text = item.get_text(" ", strip=True)
                if item_text:
                    metadata_texts.append(item_text)

        time_tag = parent_body.select_one("time")
        if time_tag is not None:
            published_at = time_tag.get_text(" ", strip=True)

        contract_type = metadata_texts[0] if len(metadata_texts) >= 1 else ""
        location = metadata_texts[1] if len(metadata_texts) >= 2 else ""
        remote_policy = metadata_texts[2] if len(metadata_texts) >= 3 else ""
        salary = ""
        sector = ""
        company_size = ""

        for item_text in metadata_texts[3:]:
            if "Salaire" in item_text:
                salary = item_text.replace("Salaire :", "").strip()
                continue
            if "collaborateur" in item_text.lower():
                company_size = item_text
                continue
            if not sector:
                sector = item_text

        raw_offer = {
            "external_id": offer_id or href.rsplit("/", maxsplit=1)[-1],
            "title": title,
            "company": company,
            "location": location,
            "salary": salary,
            "published_at": published_at,
            "skills": [],
            "url": urljoin(DEFAULT_WTTJ_BASE_URL, href),
            "description": description,
            "contract_type": contract_type,
            "remote_policy": remote_policy,
            "sector": sector,
            "company_size": company_size,
        }
        offer_cards.append(raw_offer)

    return offer_cards


def map_wttj_offer(raw_offer: dict[str, Any]) -> dict[str, Any]:
    """Convertir une offre WTTJ extraite vers le schema brut du projet."""

    return {
        "source": "welcome_to_the_jungle",
        "external_id": raw_offer.get("external_id"),
        "title": raw_offer.get("title"),
        "company": raw_offer.get("company"),
        "location": raw_offer.get("location"),
        "salary": raw_offer.get("salary"),
        "published_at": raw_offer.get("published_at"),
        "skills": raw_offer.get("skills", []),
        "raw_payload": raw_offer,
    }


def load_wttj_fallback_rows(fallback_path: Path) -> list[dict[str, Any]]:
    """Charger un CSV de secours WTTJ si present."""

    if not fallback_path.exists():
        return []

    with fallback_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return [dict(row) for row in reader]


def collect_wttj_live_rows_for_query(
    driver: webdriver.Chrome,
    query: str,
    timeout_seconds: int,
    max_pages: int,
) -> list[dict[str, Any]]:
    """Collecter les lignes WTTJ d'une requete unique via Selenium."""

    offer_rows: list[dict[str, Any]] = []
    seen_offer_ids: set[str] = set()
    is_supported, base_page_url = precheck_wttj_query_support(
        query=query,
        timeout_seconds=get_wttj_preflight_timeout_seconds(),
    )
    if not is_supported:
        return []

    last_page_number: int | None = None
    page_number = 1

    while page_number <= max_pages:
        page_url = build_wttj_metier_page_url(query=query, page_number=page_number)

        try:
            html = load_wttj_page_html(
                driver=driver,
                url=page_url,
                timeout_seconds=timeout_seconds,
            )
        except TimeoutException:
            print(
                "Welcome to the Jungle: timeout sur la page "
                f"{page_number} pour la requete '{query}'."
            )
            break
        except WebDriverException as error:
            print(
                "Welcome to the Jungle: echec Selenium sur la page "
                f"{page_number} pour la requete '{query}' : {error}"
            )
            break

        if page_number == 1:
            last_page_number = detect_wttj_last_page_number(html)

        page_offer_rows = extract_wttj_cards_from_html(html)
        print(
            "Welcome to the Jungle: "
            f"query='{query}' page={page_number} rows={len(page_offer_rows)} "
            f"url='{page_url}'"
        )

        if not page_offer_rows:
            if page_number == 1:
                offer_links = extract_wttj_offer_links_from_html(html)
                print(
                    "Welcome to the Jungle: aucune carte parsee sur la page "
                    f"metier. {len(offer_links)} lien(s) d'offre brut(s) detecte(s)."
                )
            break

        new_rows_count = 0
        for row in page_offer_rows:
            external_id = str(row.get("external_id") or "").strip()
            if not external_id:
                continue
            if external_id in seen_offer_ids:
                continue

            seen_offer_ids.add(external_id)
            offer_rows.append(row)
            new_rows_count += 1

        if new_rows_count == 0:
            print(
                "Welcome to the Jungle: aucune nouvelle offre sur la page "
                f"{page_number}, arret de la pagination."
            )
            break

        if last_page_number is not None and page_number >= last_page_number:
            break

        page_number += 1

    print(
        "Welcome to the Jungle: "
        f"{len(offer_rows)} offre(s) unique(s) conservee(s) "
        f"depuis {base_page_url}"
    )
    return offer_rows


def collect_wttj_live_rows(
    queries: list[str],
    timeout_seconds: int,
    max_pages: int,
) -> list[dict[str, Any]]:
    """Collecter les lignes WTTJ en live via Selenium pour plusieurs requetes."""

    normalized_queries = normaliser_wttj_queries(queries)
    if not normalized_queries:
        return []

    print(
        "Welcome to the Jungle: "
        f"{len(normalized_queries)} requete(s) metier a lancer : "
        + ", ".join(normalized_queries)
    )

    driver = build_wttj_webdriver()
    if driver is None:
        return []

    all_offer_rows: list[dict[str, Any]] = []
    seen_offer_ids: set[str] = set()

    try:
        for query in normalized_queries:
            query_rows = collect_wttj_live_rows_for_query(
                driver=driver,
                query=query,
                timeout_seconds=timeout_seconds,
                max_pages=max_pages,
            )

            for row in query_rows:
                external_id = str(row.get("external_id") or "").strip()
                if not external_id:
                    continue
                if external_id in seen_offer_ids:
                    continue

                seen_offer_ids.add(external_id)
                all_offer_rows.append(row)
    finally:
        driver.quit()

    print(
        "Welcome to the Jungle: "
        f"{len(all_offer_rows)} offre(s) unique(s) conservee(s) "
        f"apres deduplication globale sur {len(normalized_queries)} requete(s)."
    )
    return all_offer_rows


def collect_offres_welcome_to_the_jungle(
    query: str | None = None,
    queries: list[str] | None = None,
    query_mode: str | None = None,
    use_fallback: bool = True,
    fallback_path: Path = DEFAULT_WTTJ_FALLBACK_PATH,
) -> list[dict[str, Any]]:
    """Point d'entree principal pour la collecte Welcome to the Jungle."""

    selected_queries = build_wttj_queries(
        query=query,
        queries=queries,
        query_mode=query_mode,
    )
    timeout_seconds = get_wttj_timeout_seconds()
    max_pages = get_wttj_max_pages()

    live_rows = collect_wttj_live_rows(
        queries=selected_queries,
        timeout_seconds=timeout_seconds,
        max_pages=max_pages,
    )
    if live_rows:
        return [map_wttj_offer(row) for row in live_rows]

    if not use_fallback:
        return []

    fallback_rows = load_wttj_fallback_rows(fallback_path=fallback_path)
    if not fallback_rows:
        print(
            "Welcome to the Jungle: aucune offre live et aucun CSV de secours disponible."
        )
        return []

    print(
        "Welcome to the Jungle: utilisation du CSV de secours "
        f"'{fallback_path}'."
    )
    return [
        map_wttj_offer(
            {
                "external_id": row.get("external_id") or row.get("id"),
                "title": row.get("title") or row.get("titre"),
                "company": row.get("company") or row.get("entreprise"),
                "location": row.get("location") or row.get("lieu"),
                "salary": row.get("salary") or row.get("salaire"),
                "published_at": row.get("published_at") or row.get("date_publication"),
                "skills": json.loads(row["skills"])
                if row.get("skills", "").strip().startswith("[")
                else [],
                "url": row.get("url") or row.get("lien"),
                "description": row.get("description") or row.get("resume"),
                "contract_type": row.get("contract_type") or row.get("contrat"),
                "remote_policy": row.get("remote_policy") or row.get("teletravail"),
                "sector": row.get("sector") or row.get("secteur"),
                "company_size": row.get("company_size") or row.get("taille_entreprise"),
            }
        )
        for row in fallback_rows
    ]
