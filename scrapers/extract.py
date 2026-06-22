"""
extract.py
Reads raw_articles.json, sends each article's text to Groq's API (free tier,
Llama 3.1/3.3 model) with a strict extraction prompt, and outputs
extracted_tenders.json - a list of structured tender records, one or more
per article (an article can mention multiple projects).

Requires env var GROQ_API_KEY (set as a GitHub Actions secret).
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"  # free tier, strong extraction quality

SECTORS = ["Renewables", "Power & Distribution", "EV", "Other/Not Relevant"]
COUNTRIES = ["Saudi Arabia", "UAE", "Qatar", "Oman", "Kuwait", "Bahrain", "Unknown"]

EXTRACTION_PROMPT = """You are a precise data-extraction engine for Middle East energy tenders.

You will be given raw scraped text from a news article, press release, or
tender listing page. Extract every distinct ENERGY TENDER, RFP, RFQ, PPA
signing, contract award, or prequalification event mentioned in the text,
related to: Renewables (solar, wind, storage), Power & Distribution
(IPP/IWPP, transmission, substations, grid), or EV (charging infrastructure,
fleet procurement, EV-linked grid upgrades).

Countries in scope: Saudi Arabia, UAE, Qatar, Oman, Kuwait, Bahrain.

For each distinct tender/project event found, output an object with these
exact fields:
- "project_name": string (e.g. "Al Dibdibah Power and Al Shagaya Phase III - Zone 2")
- "country": one of {countries}
- "sector": one of {sectors}
- "stage": one of ["Announced", "RFQ/Prequalification", "RFP Issued", "Bids Received", "Shortlisted", "Awarded", "PPA Signed", "Under Construction", "Operational", "Unclear"]
- "client_authority": string (the procuring entity, e.g. "EWEC", "SPPC", "KAPP")
- "developers_bidders": array of strings (company names mentioned, empty array if none)
- "capacity_or_value": string (e.g. "500 MW", "$8.3bn", "SAR 13.35 billion" - whatever figure is given, or null)
- "deadline_or_date": string (any relevant date mentioned - submission deadline, signing date, COD - or null)
- "summary": string (one plain-English sentence, max 25 words, your own words, no quoted text)

Rules:
- If the text contains NO relevant tender/project information, return an empty array: []
- Do not invent companies, figures, or dates not present in the text
- Do not include duplicate entries for the same project within this single text
- "summary" must be a paraphrase, never copied phrasing from the source
- Return ONLY a valid JSON array. No preamble, no markdown fences, no explanation.
""".format(countries=COUNTRIES, sectors=SECTORS)


def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", file=sys.stderr)


def call_groq(article_text, retries=3):
    if not GROQ_API_KEY:
        log("ERROR: GROQ_API_KEY not set in environment")
        return None

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": article_text[:12000]},
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
    }

    for attempt in range(retries):
        try:
            resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            if resp.status_code == 429:
                wait = 5 * (attempt + 1)
                log(f"Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content
        except requests.RequestException as e:
            log(f"Groq API error (attempt {attempt+1}/{retries}): {e}")
            time.sleep(3)
        except (KeyError, IndexError) as e:
            log(f"Unexpected Groq response shape: {e}")
            return None

    return None


def parse_json_response(raw_content):
    """Strip markdown fences if present and parse JSON, with fallback recovery."""
    if raw_content is None:
        return []

    cleaned = raw_content.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
        log(f"Expected list, got {type(result)} - wrapping")
        return [result] if isinstance(result, dict) else []
    except json.JSONDecodeError as e:
        log(f"JSON parse failed: {e}. Raw content (first 300 chars): {cleaned[:300]}")
        return []


def main():
    if not os.path.exists("raw_articles.json"):
        log("ERROR: raw_articles.json not found. Run scrape.py first.")
        sys.exit(1)

    with open("raw_articles.json", "r", encoding="utf-8") as f:
        articles = json.load(f)

    all_extracted = []
    failures = 0

    for i, article in enumerate(articles):
        log(f"Extracting [{i+1}/{len(articles)}] {article['source']} - {article['url']}")
        raw_response = call_groq(article["fetched_text"])
        records = parse_json_response(raw_response)

        if not records:
            continue

        for record in records:
            if not isinstance(record, dict):
                continue
            record["source"] = article["source"]
            record["source_tier"] = article["tier"]
            record["source_url"] = article["url"]
            record["extracted_at"] = datetime.now(timezone.utc).isoformat()
            all_extracted.append(record)

        time.sleep(1)  # gentle pacing against Groq free-tier rate limits

    with open("extracted_tenders.json", "w", encoding="utf-8") as f:
        json.dump(all_extracted, f, ensure_ascii=False, indent=2)

    log(f"Extraction complete. {len(all_extracted)} tender records from {len(articles)} articles. Failures: {failures}")


if __name__ == "__main__":
    main()
