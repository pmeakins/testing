import os
import re
import requests
from typing import Any, Dict, List, Optional, Union

IPQS_API_URL = "https://www.ipqualityscore.com/api/json/phone"

# Common alias fixes
COUNTRY_ALIASES = {
    "UK": "GB",
    "EL": "GR",  # sometimes seen for Greece
}

class IPQSPhoneValidationError(Exception):
    pass

def _sanitize_phone(phone: str) -> str:
    """Keep digits and a single leading +."""
    phone = phone.strip()
    if phone.startswith("+"):
        # Keep + then digits only
        return "+" + re.sub(r"\D", "", phone[1:])
    # No plus: strip to digits
    return re.sub(r"\D", "", phone)

def _normalize_countries(countries: Optional[Union[str, List[str]]]) -> Optional[List[str]]:
    if not countries:
        return None
    if isinstance(countries, str):
        countries = [countries]
    norm = []
    for c in countries:
        if not c:
            continue
        c = c.strip().upper()
        c = COUNTRY_ALIASES.get(c, c)
        # Basic guard: ISO alpha-2 letters only
        if not re.fullmatch(r"[A-Z]{2}", c):
            raise IPQSPhoneValidationError(
                f"Invalid country code '{c}'. Use ISO-3166-1 alpha-2 (e.g., GB, US, DE)."
            )
        norm.append(c)
    return norm or None

def validate_phone(
    phone: str,
    *,
    api_key: Optional[str] = None,
    countries: Optional[Union[str, List[str]]] = None,
    strictness: int = 1,
    enhanced_line_check: bool = False,
    enhanced_name_check: bool = False,
    timeout: int = 8,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Validate a phone number & get a fraud score via IPQualityScore.
    """
    key = api_key or os.getenv("IPQS_API_KEY")
    if not key:
        raise IPQSPhoneValidationError("Missing API key. Set IPQS_API_KEY or pass api_key.")

    number = _sanitize_phone(phone)
    country_list = _normalize_countries(countries)

    headers = {"IPQS-KEY": key}
    # Base params
    params: Dict[str, Any] = {
        "phone": number,
        "strictness": strictness,
    }

    # Add country hints:
    # - If number already has +CC, you can omit country entirely.
    # - If one country: send `country=GB`
    # - If multiple: send `country[]=GB` repeatedly
    if country_list:
        if len(country_list) == 1:
            params["country"] = country_list[0]
        else:
            # requests supports sequences for same key -> pass as list of tuples
            # we'll build the request manually below to include repeated keys
            pass

    if enhanced_line_check:
        params["enhanced_line_check"] = "true"
    if enhanced_name_check:
        params["enhanced_name_check"] = "true"

    # Prepare request. Handle repeated country[]= entries if needed.
    req_params = []
    for k, v in params.items():
        if isinstance(v, list):
            for item in v:
                req_params.append((k, item))
        else:
            req_params.append((k, v))
    if country_list and len(country_list) > 1:
        for c in country_list:
            req_params.append(("country[]", c))

    if debug:
        safe = [(k, ("***" if k.lower() in {"ipqs-key"} else v)) for k, v in req_params]
        print("DEBUG request params:", safe)

    try:
        resp = requests.get(IPQS_API_URL, headers=headers, params=req_params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise IPQSPhoneValidationError(f"HTTP/parse error: {e}") from e

    # Treat API errors (including invalid phone/country) as exceptions
    if not isinstance(data, dict) or ("success" in data and data.get("success") is False):
        msg = data.get("message", "Unknown API error") if isinstance(data, dict) else "Invalid JSON"
        raise IPQSPhoneValidationError(f"API error: {msg}")

    return data

def summarize_result(data: Dict[str, Any]) -> str:
    valid = data.get("valid")
    fraud_score = data.get("fraud_score")
    line_type = data.get("line_type") or "Unknown"
    active = data.get("active")
    country = data.get("country")
    carrier = data.get("carrier") or "Unknown"
    recent_abuse = data.get("recent_abuse")
    voip = data.get("VOIP")
    risky = data.get("risky")

    if isinstance(fraud_score, int):
        if fraud_score >= 85:
            band = "HIGH"
        elif fraud_score >= 60:
            band = "ELEVATED"
        else:
            band = "LOW"
    else:
        band = "UNKNOWN"

    parts = [
        f"Valid: {valid}",
        f"Fraud Score: {fraud_score} ({band})",
        f"Country: {country}",
        f"Carrier: {carrier}",
        f"Line Type: {line_type}",
        f"Active: {active}",
        f"VOIP: {voip}",
        f"Recent Abuse: {recent_abuse}",
        f"Risky Flag: {risky}",
        f"Active Status: {data.get('active_status')}",
    ]
    return " | ".join(parts)

