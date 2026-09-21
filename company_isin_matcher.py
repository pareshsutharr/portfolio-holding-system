"""Resolve free-text company names (e.g. from a PDF portfolio statement, typos
and abbreviations included) to ISINs, using the SEBI market-cap master as the
source of truth. Mirrors gemini_mapper.py's local-match-first-then-Gemini-
fallback pattern: a confident local fuzzy match is used directly; anything
uncertain is disambiguated by Gemini, which can only choose among real
candidates from the master list -- it never invents an ISIN.
"""

from __future__ import annotations

import difflib
import json
import re

import pandas as pd
import requests

from config import GEMINI_API_KEY, MCAP_MASTER_FILE

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent"
)

AUTO_ACCEPT_SCORE = 0.80
CANDIDATE_FLOOR_SCORE = 0.35
CANDIDATES_PER_NAME = 5

_STOPWORDS = r"\b(ltd|limited|the|co|company|corporation|corp|pvt|private)\b\.?"


def _normalize(value: object) -> str:
    text = str(value or "").lower()
    text = re.sub(_STOPWORDS, "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_sorted(value: object) -> str:
    # Sorting the words makes the comparison order-invariant, so a statement name with
    # words in a different order than the master list (e.g. "Gujarat Development Mineral
    # Co." vs "Gujarat Mineral Development Corporation") still scores as a close match.
    return " ".join(sorted(_normalize(value).split()))


def _clean_response(text: str) -> str:
    return text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()


def _ask_gemini_to_disambiguate_batch(pending: list[tuple[str, list[dict]]]) -> dict[str, int | None]:
    """Ask Gemini, in a single request, which candidate (if any) matches each
    pending name. Returns {name: 0-based index into that name's candidates, or None}."""

    blocks = []
    for entry_index, (name, candidates) in enumerate(pending):
        options = "\n".join(f"  {i + 1}. {candidate['name']}" for i, candidate in enumerate(candidates))
        blocks.append(f'Entry {entry_index + 1}: "{name}"\n{options}')
    entries_text = "\n\n".join(blocks)

    prompt = f"""You are matching company names from a client's portfolio statement
against official company names from a market-cap master list. Each statement
name may contain typos, abbreviations, or reordered words. For each numbered
entry below, decide which of its candidate options (if any) is clearly the
SAME company.

{entries_text}

Rules:
1. Return ONLY valid JSON: a list with one object per entry, in order:
   [{{"entry": 1, "match": <candidate number or null>}}, ...]
2. "match" is the candidate's option number for that entry, or null if none
   of that entry's candidates are the same company.
3. No explanation.
"""
    try:
        response = requests.post(
            GEMINI_ENDPOINT,
            headers={"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=45,
        )
        response.raise_for_status()
        response_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(_clean_response(response_text))
    except (requests.RequestException, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {name: None for name, _ in pending}

    matches_by_entry = {}
    for item in parsed if isinstance(parsed, list) else []:
        if isinstance(item, dict) and isinstance(item.get("entry"), int):
            matches_by_entry[item["entry"]] = item.get("match")

    results: dict[str, int | None] = {}
    for entry_index, (name, candidates) in enumerate(pending):
        match = matches_by_entry.get(entry_index + 1)
        results[name] = (match - 1) if isinstance(match, int) and 1 <= match <= len(candidates) else None
    return results


def _load_master_names_and_isins() -> list[dict]:
    # Read the same SEBI market-cap master file market_cap.py uses, but keep the
    # company-name column too (load_market_cap_master() drops it once merged by ISIN).
    master = pd.read_excel(MCAP_MASTER_FILE, header=1)[["Company name", "ISIN"]].copy()
    master.columns = ["name", "isin"]
    master["name"] = master["name"].astype(str).str.strip()
    master["isin"] = master["isin"].astype(str).str.strip()
    return master.to_dict("records")


def resolve_company_isins(names: list[str]) -> dict[str, dict | None]:
    """Map each input company name to {"isin", "company_name", "match_type"},
    or None if no confident match (local or Gemini) could be found."""

    master_records = _load_master_names_and_isins()
    normalized_master = [(_normalize_sorted(record["name"]), record) for record in master_records]

    results: dict[str, dict | None] = {}
    pending_gemini: list[tuple[str, list[dict]]] = []

    for name in names:
        normalized_name = _normalize_sorted(name)
        scored = sorted(
            ((difflib.SequenceMatcher(None, normalized_name, candidate_norm).ratio(), record)
             for candidate_norm, record in normalized_master),
            key=lambda item: item[0],
            reverse=True,
        )
        top_score, top_record = scored[0] if scored else (0.0, None)

        if top_record and top_score >= AUTO_ACCEPT_SCORE:
            results[name] = {"isin": top_record["isin"], "company_name": top_record["name"], "match_type": "local"}
            continue

        candidates = [record for score, record in scored[:CANDIDATES_PER_NAME] if score >= CANDIDATE_FLOOR_SCORE]
        if candidates:
            pending_gemini.append((name, candidates))
        else:
            results[name] = None

    if pending_gemini:
        match_indices = _ask_gemini_to_disambiguate_batch(pending_gemini)
        for name, candidates in pending_gemini:
            match_index = match_indices.get(name)
            if match_index is None:
                results[name] = None
            else:
                record = candidates[match_index]
                results[name] = {"isin": record["isin"], "company_name": record["name"], "match_type": "gemini"}

    return results
