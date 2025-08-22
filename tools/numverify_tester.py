#!/usr/bin/env python3
"""
numverify_tester.py — works with BOTH legacy and modern numverify endpoints.

Examples
--------
# Legacy (matches your sample URL)
python numverify_tester.py "+447720313531" --legacy --pretty
python numverify_tester.py "447720313531" --legacy --pretty

# Modern (api.apilayer.com with apikey header)
python numverify_tester.py "+447720313531" --modern --pretty

Environment variables
---------------------
NUMVERIFY_ACCESS_KEY   -> used for --legacy (sent as ?access_key=...)
NUMVERIFY_API_KEY      -> used for --modern (sent as header apikey: ...)

You can also pass --key directly on the CLI.
"""
import os
import sys
import json
import argparse
import requests

LEGACY_BASE = "https://apilayer.net/api"  # legacy host (your sample)
MODERN_BASE = "https://api.apilayer.com/number_verification"  # newer host
TIMEOUT = 15

def call_legacy(number: str, country_code: str|None, key: str) -> dict:
    params = {
        "access_key": key,
        "number": number,
        # numverify docs: include country_code only for national-format numbers
        "format": 1,
    }
    if country_code and not number.strip().startswith("+"):
        params["country_code"] = country_code

    url = f"{LEGACY_BASE}/validate"
    r = requests.get(url, params=params, timeout=TIMEOUT)
    return {
        "endpoint": url,
        "http_status": r.status_code,
        "headers": dict(r.headers),
        "data": safe_json(r)
    }

def call_modern(number: str, country_code: str|None, key: str) -> dict:
    headers = {"apikey": key}
    params = {"number": number}
    if country_code and not number.strip().startswith("+"):
        params["country_code"] = country_code

    url = f"{MODERN_BASE}/validate"
    r = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    return {
        "endpoint": url,
        "http_status": r.status_code,
        "headers": dict(r.headers),
        "data": safe_json(r)
    }

def safe_json(resp: requests.Response):
    try:
        return resp.json()
    except Exception:
        return {"_raw": resp.text}

def main():
    ap = argparse.ArgumentParser(description="Test numverify API (legacy or modern).")
    ap.add_argument("number", help="Phone number (international like +44..., or national with --country-code)")
    ap.add_argument("-c", "--country-code", help="2-letter ISO country (e.g., GB, US) for national numbers")
    ap.add_argument("--key", help="API key (overrides env vars)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--legacy", action="store_true", help="Use legacy apilayer.net endpoint (access_key in query)")
    mode.add_argument("--modern", action="store_true", help="Use modern api.apilayer.com endpoint (apikey header)")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    # Decide mode: default to legacy to match your sample URL
    use_legacy = True if not args.modern else False
    if args.legacy:
        use_legacy = True
    if args.modern:
        use_legacy = False

    # Pick key source
    if use_legacy:
        key = args.key or os.getenv("NUMVERIFY_ACCESS_KEY")
        if not key:
            print("Set NUMVERIFY_ACCESS_KEY (or pass --key) for legacy endpoint.", file=sys.stderr)
            sys.exit(2)
        result = call_legacy(args.number, args.country_code, key)
    else:
        key = args.key or os.getenv("NUMVERIFY_API_KEY")
        if not key:
            print("Set NUMVERIFY_API_KEY (or pass --key) for modern endpoint.", file=sys.stderr)
            sys.exit(2)
        result = call_modern(args.number, args.country_code, key)

    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))

if __name__ == "__main__":
    main()

