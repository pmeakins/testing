#!/usr/bin/env python3
"""
ipqs_cli.py — IPQualityScore multi-endpoint CLI

Usage examples:
  export IPQS_API_KEY=YOUR_KEY
  python ipqs_cli.py ip 1.2.3.4
  python ipqs_cli.py ip 1.2.3.4 --strictness 1 --fast
  python ipqs_cli.py email test@example.com
  python ipqs_cli.py phone +447700900123 --country GB
  python ipqs_cli.py url https://suspicious.example
  python ipqs_cli.py ip 1.2.3.4 --json   # raw JSON output

Notes:
- API key comes from env var IPQS_API_KEY or --api-key.
- Add --json to print exact API JSON.
"""

import argparse
import json
import os
import sys
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://ipqualityscore.com/api/json"

def make_session(timeout=10):
    s = requests.Session()
    retries = Retry(
        total=5,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"])
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.timeout = timeout
    return s

def env_or_arg_api_key(args):
    key = args.api_key or os.environ.get("IPQS_API_KEY")
    if not key:
        print("Error: API key not provided. Set IPQS_API_KEY or use --api-key.", file=sys.stderr)
        sys.exit(2)
    return key

def req(session, path, params=None):
    url = f"{BASE}/{path}"
    r = session.get(url, params=params or {}, timeout=session.timeout)
    r.raise_for_status()
    return r.json()

def summarize_ip(data):
    parts = []
    fs = data.get("fraud_score")
    ip = data.get("request")
    country = data.get("country_code")
    parts.append(f"IP: {ip}  Country: {country}  FraudScore: {fs}")
    flags = []
    for k in ("proxy","vpn","tor","bot_status","recent_abuse","leaked","mobile","corporate_proxy","active_vpn"):
        v = data.get(k)
        if isinstance(v, bool) and v:
            flags.append(k)
    if flags:
        parts.append("Flags: " + ", ".join(flags))
    risk = data.get("risk_score") or fs
    if risk is not None:
        level = "LOW"
        try:
            risk_val = float(risk)
            if risk_val >= 85: level = "CRITICAL"
            elif risk_val >= 75: level = "HIGH"
            elif risk_val >= 50: level = "MEDIUM"
        except Exception:
            pass
        parts.append(f"Risk level: {level}")
    reason = data.get("message") or data.get("region") or ""
    if reason:
        parts.append(f"Note: {reason}")
    return "\n".join(parts)

def summarize_email(data):
    email = data.get("request")
    valid = data.get("valid")
    fs = data.get("fraud_score")
    disposable = data.get("disposable")
    deliverability = data.get("deliverability")
    recent_abuse = data.get("recent_abuse")
    domain = data.get("domain")
    parts = [
        f"Email: {email} (domain: {domain})",
        f"Valid: {valid}  Deliverability: {deliverability}  FraudScore: {fs}",
        f"Disposable: {disposable}  Recent Abuse: {recent_abuse}",
    ]
    if data.get("message"):
        parts.append(f"Note: {data['message']}")
    return "\n".join(parts)

def summarize_phone(data):
    phone = data.get("request")
    valid = data.get("valid")
    fs = data.get("fraud_score")
    active = data.get("active")
    carrier = data.get("carrier")
    line_type = data.get("line_type")
    country = data.get("country")
    recent_abuse = data.get("recent_abuse")
    parts = [
        f"Phone: {phone}  Country: {country}",
        f"Valid: {valid}  Active: {active}  Line Type: {line_type}  Carrier: {carrier}",
        f"FraudScore: {fs}  Recent Abuse: {recent_abuse}",
    ]
    if data.get("message"):
        parts.append(f"Note: {data['message']}")
    return "\n".join(parts)

def summarize_url(data):
    url = data.get("request")
    fs = data.get("fraud_score")
    suspicious = data.get("suspicious")
    unsafe = data.get("unsafe")
    phishing = data.get("phishing")
    malware = data.get("malware")
    risk_score = data.get("risk_score") or fs
    parts = [
        f"URL: {url}",
        f"FraudScore: {fs}  RiskScore: {risk_score}",
        f"Suspicious: {suspicious}  Unsafe: {unsafe}  Phishing: {phishing}  Malware: {malware}",
    ]
    if data.get("message"):
        parts.append(f"Note: {data['message']}")
    return "\n".join(parts)

def cmd_ip(args):
    key = env_or_arg_api_key(args)
    session = make_session(timeout=args.timeout)
    # Common IP params:
    params = {
        "strictness": args.strictness,
        "fast": str(args.fast).lower(),
        "allow_public_access_points": str(args.allow_public_access_points).lower(),
        "mobile": str(args.mobile).lower(),
        "lighter_penalties": str(args.lighter_penalties).lower(),
        "transaction_strictness": args.transaction_strictness,
        "user_agent": args.user_agent or "",
    }
    # Endpoint path: ip/{API_KEY}/{IP}
    path = f"ip/{key}/{quote(args.ip)}"
    data = req(session, path, params)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(summarize_ip(data))

def cmd_email(args):
    key = env_or_arg_api_key(args)
    session = make_session(timeout=args.timeout)
    params = {
        "timeout": args.lookup_timeout,
        "fast": str(args.fast).lower(),
        "strictness": args.strictness,
        "suggest_domain": str(args.suggest_domain).lower(),
    }
    path = f"email/{key}/{quote(args.email)}"
    data = req(session, path, params)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(summarize_email(data))

def cmd_phone(args):
    key = env_or_arg_api_key(args)
    session = make_session(timeout=args.timeout)
    params = {
        "country": args.country or "",
        "strictness": args.strictness,
        "line_type_detect": str(args.line_type_detect).lower(),
        "fast": str(args.fast).lower(),
    }
    path = f"phone/{key}/{quote(args.phone)}"
    data = req(session, path, params)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(summarize_phone(data))

def cmd_url(args):
    key = env_or_arg_api_key(args)
    session = make_session(timeout=args.timeout)
    params = {
        "strictness": args.strictness,
        "fast": str(args.fast).lower(),
        "risk_score": "true",
        "malware": "true",
        "phishing": "true",
    }
    path = f"url/{key}/{quote(args.url, safe='')}"
    data = req(session, path, params)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(summarize_url(data))

def main():
    parser = argparse.ArgumentParser(description="IPQualityScore CLI")
    parser.add_argument("--api-key", help="IPQS API key (or set IPQS_API_KEY)")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout seconds (default 10)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of summary")

    sub = parser.add_subparsers(dest="command", required=True)

    # IP
    p_ip = sub.add_parser("ip", help="Check an IP address")
    p_ip.add_argument("ip", help="IP to check (IPv4/IPv6)")
    p_ip.add_argument("--strictness", type=int, default=1, choices=[0,1,2],
                      help="0–2 (higher = stricter, more false positives). Default 1.")
    p_ip.add_argument("--fast", action="store_true", help="Faster but slightly less accurate")
    p_ip.add_argument("--allow-public-access-points", action="store_true",
                      help="Allow coffeeshop/hotel WiFi to reduce false positives")
    p_ip.add_argument("--mobile", action="store_true", help="Assume mobile devices more likely")
    p_ip.add_argument("--lighter-penalties", action="store_true", help="Lighter penalties for risk signals")
    p_ip.add_argument("--transaction-strictness", type=int, default=1, choices=[0,1,2],
                      help="Adjusts scoring for transactional checks")
    p_ip.add_argument("--user-agent", help="Optional user agent to improve accuracy")
    p_ip.set_defaults(func=cmd_ip)

    # Email
    p_email = sub.add_parser("email", help="Validate an email")
    p_email.add_argument("email", help="Email address to check")
    p_email.add_argument("--strictness", type=int, default=1, choices=[0,1,2],
                         help="0–2. Higher = stricter. Default 1.")
    p_email.add_argument("--lookup-timeout", type=int, default=7,
                         help="Mailbox lookup timeout seconds (default 7)")
    p_email.add_argument("--fast", action="store_true", help="Faster but slightly less accurate")
    p_email.add_argument("--suggest-domain", action="store_true",
                         help="Return a typo-corrected domain suggestion")
    p_email.set_defaults(func=cmd_email)

    # Phone
    p_phone = sub.add_parser("phone", help="Validate a phone number")
    p_phone.add_argument("phone", help="Phone number (E.164 like +447...)")
    p_phone.add_argument("--country", help="2-letter country code if number lacks prefix")
    p_phone.add_argument("--strictness", type=int, default=1, choices=[0,1,2],
                         help="0–2. Higher = stricter. Default 1.")
    p_phone.add_argument("--line-type-detect", action="store_true", help="Return line type (mobile/fixed/VoIP)")
    p_phone.add_argument("--fast", action="store_true", help="Faster but slightly less accurate")
    p_phone.set_defaults(func=cmd_phone)

    # URL
    p_url = sub.add_parser("url", help="Scan a URL")
    p_url.add_argument("url", help="URL to scan (include scheme)")
    p_url.add_argument("--strictness", type=int, default=1, choices=[0,1,2],
                       help="0–2. Higher = stricter. Default 1.")
    p_url.add_argument("--fast", action="store_true", help="Faster but slightly less accurate")
    p_url.set_defaults(func=cmd_url)

    args = parser.parse_args()
    try:
        args.func(args)
    except requests.HTTPError as e:
        # Graceful display for IPQS errors
        msg = ""
        try:
            msg = e.response.json().get("message", "")
        except Exception:
            pass
        print(f"HTTP error: {e.response.status_code} {e.response.reason}. {msg}".strip(), file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

