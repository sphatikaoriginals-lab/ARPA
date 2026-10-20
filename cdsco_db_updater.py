#!/usr/bin/env python3
"""
CDSCO Scraper & Direct ARPA SQLite Cache Updater
================================================
Crawls CDSCO approval notices, extracts text, identifies new molecules/FDCs,
and directly writes/updates 'drug_cache.db'.
"""

import csv
import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# --------------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------------

DB_PATH = "drug_cache.db"
BASE_URL = "https://cdsco.gov.in"

SEED_PAGES = [
    "/opencms/opencms/en/Drugs/New-Drugs/",
    "/opencms/opencms/en/Drugs/Subsequent-New-Drugs/",
    "/opencms/opencms/en/Drugs/FDC/",
    "/opencms/opencms/en/Notifications/Public-Notices/",
    "/opencms/opencms/en/Notifications/Circulars/",
    "/opencms/opencms/en/Notifications/Archive/",
    "/opencms/opencms/en/Notifications/Gazette-Notifications/",
    "/opencms/opencms/en/Notifications/documents/",
]

OUTPUT_DIR = "output"
PDF_DIR = os.path.join(OUTPUT_DIR, "pdfs")
RAW_CSV = os.path.join(OUTPUT_DIR, "raw_notices.csv")

SLEEP_SECONDS = 1.2
REQUEST_TIMEOUT = 30
MAX_PDF_MB = 25

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ARPA-ResearchBot/1.0; +for-healthcare-data-indexing)"
    )
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("cdsco_updater")

DRUG_NAME_PATTERNS = [
    re.compile(r"approv(?:al|ed)\s+(?:of|for)\s+([A-Z][A-Za-z0-9\-\s\+]{2,60}?)(?:\s+(?:tablet|capsule|injection|for|in|indicated))", re.IGNORECASE),
    re.compile(r"permission\s+to\s+(?:manufacture|import)\s+(?:and\s+market\s+)?([A-Z][A-Za-z0-9\-\s\+]{2,60}?)(?:\s+(?:tablet|capsule|injection|for|in))", re.IGNORECASE),
    re.compile(r"fixed\s+dose\s+combination\s+of\s+([A-Za-z0-9\-\s\+]{3,80})", re.IGNORECASE),
]

DATE_PATTERN = re.compile(
    r"(\d{1,2}[-/. ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/. ]\d{2,4})",
    re.IGNORECASE,
)

# --------------------------------------------------------------------------
# DATABASE HELPERS
# --------------------------------------------------------------------------

def init_db(db_path: str = DB_PATH):
    """Ensures the salt_cache table exists."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS salt_cache (
            brand_name TEXT PRIMARY KEY,
            salts TEXT NOT NULL,
            source TEXT DEFAULT 'CDSCO',
            last_updated TEXT
        )
    """)
    conn.commit()
    conn.close()

def clean_drug_string(name: str) -> str:
    """Removes dosage forms and special characters."""
    cleaned = re.sub(r'\b(tablet|tablets|capsule|capsules|injection|syrup|gel|ointment|solution|oral)\b', '', name, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b\d+(\.\d+)?\s*(mg|mcg|ml|g|iu|%)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^\w\s\+]', ' ', cleaned)
    return " ".join(cleaned.split()).strip()

def parse_salts_list(raw_candidate: str) -> list[str]:
    """Splits Fixed Dose Combinations (FDCs) joined by +, plus, and, with."""
    cleaned = clean_drug_string(raw_candidate)
    if not cleaned:
        return []
    
    # Split combinations: "Drug A + Drug B" or "Drug A and Drug B"
    parts = re.split(r'\s*\+\s*|\s+plus\s+|\s+and\s+|\s+with\s+', cleaned, flags=re.IGNORECASE)
    salts = [p.strip().title() for p in parts if len(p.strip()) >= 2]
    return salts

def upsert_drug_to_db(drug_raw_name: str, db_path: str = DB_PATH) -> int:
    """Inserts parsed molecules into SQLite cache."""
    salts = parse_salts_list(drug_raw_name)
    if not salts:
        return 0

    brand_key = clean_drug_string(drug_raw_name).lower()
    salts_json = json.dumps(salts)
    now_str = datetime.now().isoformat()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Store full combination / brand entry
        cursor.execute("""
            INSERT OR REPLACE INTO salt_cache (brand_name, salts, source, last_updated)
            VALUES (?, ?, 'CDSCO_APPROVAL', ?)
        """, (brand_key, salts_json, now_str))

        # 2. Store individual active components as self-resolving generic keys
        for salt in salts:
            salt_key = salt.lower().strip()
            cursor.execute("""
                INSERT OR IGNORE INTO salt_cache (brand_name, salts, source, last_updated)
                VALUES (?, ?, 'CDSCO_SALT', ?)
            """, (salt_key, json.dumps([salt]), now_str))

        conn.commit()
        conn.close()
        return 1
    except Exception as e:
        log.warning("Database write failed for '%s': %s", drug_raw_name, e)
        return 0

# --------------------------------------------------------------------------
# SCRAPING & PDF HELPERS
# --------------------------------------------------------------------------

def safe_get(url, **kwargs):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, **kwargs)
        if resp.status_code != 200:
            log.warning("Non-200 (%s) for %s", resp.status_code, url)
            return None
        return resp
    except requests.RequestException as e:
        log.warning("Request failed for %s: %s", url, e)
        return None

def find_pdf_links(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            row_text = " | ".join(c.get_text(strip=True) for c in cells)
            link_tag = row.find("a", href=True)
            if link_tag and _looks_like_pdf(link_tag["href"]):
                pdf_url = urljoin(page_url, link_tag["href"])
                title = cells[1].get_text(strip=True) if len(cells) > 1 else link_tag.get_text(strip=True)
                date_match = DATE_PATTERN.search(row_text)
                date_str = date_match.group(1) if date_match else ""
                results.append((title or "Untitled", date_str, pdf_url))

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if _looks_like_pdf(href):
            pdf_url = urljoin(page_url, href)
            if not any(pdf_url == r[2] for r in results):
                title = a.get_text(strip=True) or "Untitled"
                results.append((title, "", pdf_url))

    return results

def _looks_like_pdf(href):
    href_lower = href.lower()
    return (
        href_lower.endswith(".pdf")
        or "download_file_division.jsp" in href_lower
        or ".doc" in href_lower
    )

def download_pdf(pdf_url, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    parsed = urlparse(pdf_url)
    fname = os.path.basename(parsed.path) or "notice.pdf"
    if not re.search(r"\.\w{2,4}$", fname):
        fname += ".pdf"
    fname = re.sub(r"[^A-Za-z0-9._-]", "_", fname)
    local_path = os.path.join(dest_dir, fname)

    resp = safe_get(pdf_url, stream=True)
    if resp is None:
        return None

    try:
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return local_path
    except OSError as e:
        log.warning("Failed to save %s: %s", pdf_url, e)
        return None

def extract_pdf_text(pdf_path):
    if pdfplumber is None or not pdf_path.lower().endswith(".pdf"):
        return ""
    text_chunks = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:8]:
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)
    except Exception as e:
        log.warning("Failed to extract text from %s: %s", pdf_path, e)
        return ""
    return "\n".join(text_chunks)

def parse_drug_mentions(text):
    found = []
    for pattern in DRUG_NAME_PATTERNS:
        for match in pattern.finditer(text):
            candidate = match.group(1).strip(" -")
            if 3 <= len(candidate) <= 80:
                found.append(candidate)
    return list(set(found))

# --------------------------------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------------------------------

def update_arpa_db():
    init_db(DB_PATH)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)

    all_notices = []
    for path in SEED_PAGES:
        page_url = urljoin(BASE_URL, path)
        log.info("Crawling listing: %s", page_url)
        resp = safe_get(page_url)
        time.sleep(SLEEP_SECONDS)
        if resp:
            notices = find_pdf_links(resp.text, page_url)
            log.info("  Found %d notices.", len(notices))
            for title, d_str, p_url in notices:
                all_notices.append((title, d_str, p_url, page_url))

    # De-duplicate by PDF URL
    seen_urls = set()
    deduped = []
    for item in all_notices:
        if item[2] not in seen_urls:
            seen_urls.add(item[2])
            deduped.append(item)

    log.info("Total unique notices to process: %d", len(deduped))

    records_inserted = 0
    with open(RAW_CSV, "w", newline="", encoding="utf-8") as f_raw:
        raw_writer = csv.writer(f_raw)
        raw_writer.writerow(["title", "notice_date", "pdf_url", "found_on_page", "local_path"])

        for i, (title, date_str, pdf_url, seed_page) in enumerate(deduped, 1):
            log.info("[%d/%d] Downloading: %s", i, len(deduped), pdf_url)
            local_path = download_pdf(pdf_url, PDF_DIR)
            time.sleep(SLEEP_SECONDS)

            raw_writer.writerow([title, date_str, pdf_url, seed_page, local_path or ""])
            f_raw.flush()

            if local_path:
                # 1. Try parsing directly from notice title
                candidates = parse_drug_mentions(title)

                # 2. Extract and parse from PDF content
                pdf_text = extract_pdf_text(local_path)
                if pdf_text:
                    candidates.extend(parse_drug_mentions(pdf_text))

                for candidate in set(candidates):
                    count = upsert_drug_to_db(candidate, DB_PATH)
                    records_inserted += count
                    if count:
                        log.info("  [DB SUCCESS] Indexed CDSCO Molecule: %s", candidate)

    log.info("=" * 60)
    log.info("CDSCO Database Synchronization Complete.")
    log.info("Total new/updated chemical entities in '%s': %d", DB_PATH, records_inserted)
    log.info("=" * 60)

if __name__ == "__main__":
    start = datetime.now()
    update_arpa_db()
    log.info("Elapsed: %s", datetime.now() - start)