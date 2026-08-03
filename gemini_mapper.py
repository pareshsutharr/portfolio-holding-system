import json
import re

import requests

from config import GEMINI_API_KEY

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent"
)

# =====================================
# STANDARD FIELDS
# =====================================

STANDARD_FIELDS = [
    "security_name",
    "isin",
    "quantity",
    "closing_value"
]

HEADER_ALIASES = {
    "security_name": ("stock name", "security name", "company name", "scrip name"),
    "isin": ("isin", "isin code"),
    "quantity": ("quantity", "qty", "units"),
    "closing_value": (
        "closing value",
        "market value",
        "current value",
        "valuation",
    ),
}


def _normalize_header(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def get_local_mapping(headers):
    """Map common statement headers without requiring an external API."""
    normalized = {_normalize_header(header): header for header in headers}
    return {
        field: next(
            (normalized[alias] for alias in aliases if alias in normalized),
            None,
        )
        for field, aliases in HEADER_ALIASES.items()
    }

# =====================================
# BUILD PROMPT
# =====================================

def build_prompt(headers):

    return f"""
You are a portfolio statement expert.

Map the following Excel headers to the standard fields.

Standard Fields

- security_name
- isin
- quantity
- closing_value

Headers

{headers}

Rules

1. Return ONLY valid JSON.
2. No explanation.
3. Every field must exist.
4. If not found, return null.

Example

{{
    "security_name":"Stock Name",
    "isin":"ISIN",
    "quantity":"Quantity",
    "closing_value":"Closing Value"
}}
"""

# =====================================
# CLEAN GEMINI RESPONSE
# =====================================

def clean_response(text):

    text = text.strip()

    text = text.replace("```json", "")
    text = text.replace("```", "")

    return text.strip()

# =====================================
# VALIDATE RESPONSE
# =====================================

def validate_mapping(mapping):

    for field in STANDARD_FIELDS:

        if field not in mapping:

            raise Exception(
                f"{field} missing from Gemini response."
            )

# =====================================
# GET COLUMN MAPPING
# =====================================

def get_column_mapping(headers):
    local_mapping = get_local_mapping(headers)
    if all(local_mapping.values()):
        print("\n========== COLUMN MAPPING (LOCAL) ==========\n")
        print(json.dumps(local_mapping, indent=4))
        return local_mapping

    prompt = build_prompt(headers)

    try:
        response = requests.post(
            GEMINI_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": GEMINI_API_KEY,
            },
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        response.raise_for_status()

        response_text = (
            response.json()["candidates"][0]["content"]["parts"][0]["text"]
        )

        print("\n========== GEMINI RESPONSE ==========\n")

        print(response_text)

        clean_text = clean_response(
            response_text
        )

        mapping = json.loads(clean_text)

        validate_mapping(mapping)
    except (requests.RequestException, KeyError, TypeError, json.JSONDecodeError) as exc:
        missing = [field for field, header in local_mapping.items() if header is None]
        raise RuntimeError(
            "Could not map required portfolio columns. "
            f"Missing local matches for: {', '.join(missing)}; "
            f"Gemini request failed: {exc}"
        ) from exc

    print("\n========== COLUMN MAPPING ==========\n")

    print(
        json.dumps(
            mapping,
            indent=4
        )
    )

    return mapping
