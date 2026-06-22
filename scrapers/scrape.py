"""
scrape.py
Fetches raw content from all sources in sources.py.
Outputs raw_articles.json - a list of {source, country, tier, url, fetched_text, fetched_at}
for extract.py to process with the Groq API.

This script is deliberately conservative: if a fetch fails, it logs and
continues rather than crashing the whole run.
"""

import json
import time
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from sources import SOURCES, SECTOR_KEYWORDS, COUNTRIES

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 20
DELAY_BETWEEN_REQUESTS = 2  # be polite, avoid hammering small gov/news sites


def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", file=sys.stderr)


def fetch_page(url):
    """Fetch a URL and return cleaned visible text, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        log(f"FAILED fetch: {url} -> {e}")
        return None

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        # strip non-content tags
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # collapse excessive blank lines
        lines = [l for l in text.split("\n") if l.strip()]
        return "\n".join(lines)
    except Exception as e:
        log(f"FAILED parse: {url} -> {e}")
        return None


def build_search_url(template, query):
    return template.replace("{query}", requests.utils.quote(query))


def collect_articles():
    articles = []
    fetched_count = 0
    failed_count = 0

    for source in SOURCES:
        name = source["name"]
        tier = source["tier"]
        country = source["country"]
        url_template = source["url"]

        urls_to_try = []

        if "{query}" in url_template:
            # search-style source: build one query per sector, capped to
            # keep request volume sane on a weekly free-tier run
            for sector, keywords in SECTOR_KEYWORDS.items():
                # use the first (most specific) keyword per sector per source
                query = keywords[0]
                if country != "regional":
                    query = f"{query} {country}"
                urls_to_try.append((build_search_url(url_template, query), sector))
        else:
            # static landing/news page - fetch once, sector tagged as "unknown"
            # (extraction step will determine actual sector from content)
            urls_to_try.append((url_template, None))

        for url, sector_hint in urls_to_try:
            log(f"Fetching [{name}] {url}")
            text = fetch_page(url)
            time.sleep(DELAY_BETWEEN_REQUESTS)

            if text is None:
                failed_count += 1
                continue

            if len(text) < 200:
                log(f"SKIP (too little content, {len(text)} chars): {url}")
                continue

            fetched_count += 1
            articles.append({
                "source": name,
                "tier": tier,
                "country": country,
                "sector_hint": sector_hint,
                "url": url,
                "fetched_text": text[:15000],  # cap per-page text sent downstream
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })

    log(f"Done. Fetched: {fetched_count}, Failed: {failed_count}")
    return articles


def main():
    articles = collect_articles()
    with open("raw_articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    log(f"Wrote {len(articles)} articles to raw_articles.json")


if __name__ == "__main__":
    main()
