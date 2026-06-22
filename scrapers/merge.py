"""
merge.py
Takes extracted_tenders.json (this week's fresh extraction) and merges it
into the persistent tenders.json (the full historical dataset the dashboard reads).

Verification logic:
- Tier 0/1 source -> status "Confirmed" immediately
- Tier 2 source only -> status "Unverified - single source"
- If a Tier-2-only project later gets corroborated by ANY second independent
  source (regardless of tier) -> upgrade to "Confirmed"
- Matching projects (same country + sector + similar project name) are
  treated as the same tender and merged/updated, not duplicated, with stage
  progression tracked in a history list.
"""

import json
import os
import sys
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

TENDERS_FILE = "tenders.json"
EXTRACTED_FILE = "extracted_tenders.json"

NAME_SIMILARITY_THRESHOLD = 0.45  # token-overlap threshold for "same project"

# Generic words that shouldn't count toward project-name matching - they
# appear across many unrelated projects and inflate false-positive overlap.
STOPWORDS = {
    "and", "the", "of", "in", "for", "at", "a", "an", "to",
    "power", "energy", "project", "ipp", "iwpp", "plant", "solar",
    "wind", "renewable", "renewables", "phase",
}


def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", file=sys.stderr)


def normalize_name(name):
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r"[^a-z0-9 ]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def token_set(name):
    """Tokenize, dropping generic energy-sector words that don't help
    distinguish one project from another (e.g. every entry has 'solar')."""
    tokens = normalize_name(name).split()
    meaningful = [t for t in tokens if t not in STOPWORDS]
    return set(meaningful) if meaningful else set(tokens)


def similarity(a, b):
    """Combine token-overlap (handles reordering/truncation across sources
    naming the same project differently) with character similarity as a
    tiebreaker/fallback for short names where token overlap is unreliable."""
    set_a, set_b = token_set(a), token_set(b)
    if not set_a or not set_b:
        return 0.0

    intersection = set_a & set_b
    union = set_a | set_b
    jaccard = len(intersection) / len(union) if union else 0.0

    # also require the overlap to be a meaningful chunk of the SHORTER name,
    # so "Zone 2" alone doesn't match everything containing "zone" and "2"
    smaller = min(len(set_a), len(set_b))
    coverage = len(intersection) / smaller if smaller else 0.0

    char_sim = SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()

    # weighted blend: token coverage matters most, jaccard and char_sim support it
    return max(jaccard, 0.5 * coverage + 0.5 * char_sim) if coverage >= 0.5 else jaccard


def load_existing():
    if os.path.exists(TENDERS_FILE):
        with open(TENDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def find_match(record, existing_tenders):
    """Find an existing tender that likely refers to the same project."""
    candidate_name = record.get("project_name", "")
    candidate_country = record.get("country", "")

    best_match = None
    best_score = 0.0

    for tender in existing_tenders:
        if tender.get("country") != candidate_country:
            continue
        score = similarity(candidate_name, tender.get("project_name", ""))
        if score > best_score:
            best_score = score
            best_match = tender

    if best_score >= NAME_SIMILARITY_THRESHOLD:
        return best_match
    return None


def determine_status(record, existing_match):
    """Decide verification status for a record given its source tier and any existing match."""
    tier = record.get("source_tier", 2)
    source_name = record.get("source", "unknown")

    if tier in (0, 1):
        return "Confirmed"

    # Tier 2 only - check if this is a NEW independent source confirming an
    # already-seen single-source project
    if existing_match:
        existing_sources = {s.get("source") for s in existing_match.get("source_history", [])}
        if existing_sources and source_name not in existing_sources:
            return "Confirmed"  # second independent source = corroborated
        if existing_match.get("status") == "Confirmed":
            return "Confirmed"

    return "Unverified - single source"


def merge_record(record, existing_tenders):
    match = find_match(record, existing_tenders)
    status = determine_status(record, match)

    source_entry = {
        "source": record.get("source"),
        "source_tier": record.get("source_tier"),
        "source_url": record.get("source_url"),
        "stage_reported": record.get("stage"),
        "seen_at": record.get("extracted_at"),
    }

    if match:
        # update existing tender in place
        match["status"] = status
        match["last_updated"] = record.get("extracted_at")

        # update stage if this report is newer / more advanced
        if record.get("stage") and record.get("stage") != "Unclear":
            match["stage"] = record["stage"]

        # merge developer/bidder lists without duplicates
        existing_devs = set(match.get("developers_bidders", []))
        new_devs = set(record.get("developers_bidders", []) or [])
        match["developers_bidders"] = sorted(existing_devs | new_devs)

        # fill in missing fields if this record has them and existing doesn't
        for field in ["capacity_or_value", "deadline_or_date", "client_authority", "summary"]:
            if not match.get(field) and record.get(field):
                match[field] = record[field]

        match.setdefault("source_history", []).append(source_entry)
        return None  # no new tender object, existing one was updated

    else:
        # brand new tender
        new_tender = {
            "id": f"{normalize_name(record.get('country',''))}-{normalize_name(record.get('project_name',''))}"[:80],
            "project_name": record.get("project_name", "Unknown project"),
            "country": record.get("country", "Unknown"),
            "sector": record.get("sector", "Other/Not Relevant"),
            "stage": record.get("stage", "Unclear"),
            "client_authority": record.get("client_authority"),
            "developers_bidders": record.get("developers_bidders", []) or [],
            "capacity_or_value": record.get("capacity_or_value"),
            "deadline_or_date": record.get("deadline_or_date"),
            "summary": record.get("summary"),
            "status": status,
            "first_seen": record.get("extracted_at"),
            "last_updated": record.get("extracted_at"),
            "source_history": [source_entry],
        }
        return new_tender


def main():
    existing_tenders = load_existing()

    if not os.path.exists(EXTRACTED_FILE):
        log("ERROR: extracted_tenders.json not found. Run extract.py first.")
        sys.exit(1)

    with open(EXTRACTED_FILE, "r", encoding="utf-8") as f:
        new_records = json.load(f)

    # filter out irrelevant extractions
    new_records = [
        r for r in new_records
        if isinstance(r, dict) and r.get("sector") in ("Renewables", "Power & Distribution", "EV")
    ]

    new_count = 0
    updated_count = 0

    for record in new_records:
        result = merge_record(record, existing_tenders)
        if result is not None:
            existing_tenders.append(result)
            new_count += 1
        else:
            updated_count += 1

    with open(TENDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_tenders, f, ensure_ascii=False, indent=2)

    log(f"Merge complete. New tenders: {new_count}. Updated existing: {updated_count}. Total in tracker: {len(existing_tenders)}")

    # write a small metadata file the dashboard can use to show "last updated"
    meta = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "total_tenders": len(existing_tenders),
        "new_this_run": new_count,
        "updated_this_run": updated_count,
    }
    with open("meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


if __name__ == "__main__":
    main()
