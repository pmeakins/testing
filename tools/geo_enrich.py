#!/usr/bin/env python3
"""
geo_enrich.py — WhoisXML IP Geolocation enrichment for a domain.

- Resolves A/AAAA for the input domain
- Queries ip-geolocation.whoisxmlapi.com for each resolved IP (reverseIp=1)
- If no A/AAAA, tries domain-based lookup
- Prints a single JSON object you can feed to a Jinja template

Env:
  WHOISXML_API_KEY  - your API key

Usage:
  python geo_enrich.py example.com
"""

import os
import sys
import json
import socket
from typing import Dict, Any, List
import requests

try:
    import dns.resolver
except ImportError:
    print("Please `pip install dnspython requests`", file=sys.stderr)
    sys.exit(2)

API_BASE = "https://ip-geolocation.whoisxmlapi.com/api/v1"
TIMEOUT = 15

def resolve_ips(domain: str) -> Dict[str, List[str]]:
    res = dns.resolver.Resolver()
    res.lifetime = 5.0
    res.timeout = 5.0
    out = {"A": [], "AAAA": []}
    for rr in ("A", "AAAA"):
        try:
            out[rr] = [r.to_text().split()[0] for r in res.resolve(domain, rr)]
        except Exception:
            out[rr] = []
    return out

def geo_lookup_ip(api_key: str, ip: str, reverse_ip: bool = True) -> Dict[str, Any]:
    params = {
        "apiKey": api_key,
        "ipAddress": ip,
        "reverseIp": 1 if reverse_ip else 0,
        "outputFormat": "JSON",
    }
    r = requests.get(API_BASE, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def geo_lookup_domain(api_key: str, domain: str) -> Dict[str, Any]:
    params = {
        "apiKey": api_key,
        "domain": domain,
        "outputFormat": "JSON",
        # reverseIp is only meaningful for IP lookups; omit here
    }
    r = requests.get(API_BASE, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def summarize_payload(p: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pull out common fields for easy templating. Keep the full raw as 'raw'.
    Payload shape is controlled by WhoisXML; fields below are defensive.
    """
    loc = p.get("location", {}) if isinstance(p.get("location"), dict) else p
    net = p.get("connection", {}) if isinstance(p.get("connection"), dict) else p
    asn = p.get("asn", {}) if isinstance(p.get("asn"), dict) else p

    return {
        "ip": p.get("ip") or p.get("ipAddress"),
        "domain": p.get("domain"),
        "continent": loc.get("continent", {}).get("name") if isinstance(loc.get("continent"), dict) else None,
        "country": (loc.get("country", {}).get("name") if isinstance(loc.get("country"), dict)
                    else loc.get("country")),
        "country_code": (loc.get("country", {}).get("code") if isinstance(loc.get("country"), dict)
                         else loc.get("countryCode")),
        "region": loc.get("region") or loc.get("stateProv"),
        "city": loc.get("city"),
        "postal_code": loc.get("postalCode") or loc.get("zipCode"),
        "lat": loc.get("lat") or loc.get("latitude"),
        "lon": loc.get("lng") or loc.get("longitude"),
        "timezone": loc.get("timeZone") or loc.get("timezone"),
        "isp": net.get("isp") or p.get("isp"),
        "org": net.get("organization") or p.get("organization"),
        "connection_type": net.get("connectionType") or p.get("connectionType"),
        "asn": (asn.get("asn") if isinstance(asn, dict) else p.get("asn")),
        "as_org": (asn.get("name") if isinstance(asn, dict) else p.get("asName")),
        "reverse_domains": p.get("reverseIp", {}).get("domains") if isinstance(p.get("reverseIp"), dict) else p.get("domains"),
        "raw": p,  # keep everything
    }

def main():
    if len(sys.argv) != 2:
        print("Usage: python geo_enrich.py <domain>", file=sys.stderr)
        sys.exit(1)

    domain = sys.argv[1].strip().lower()
    api_key = os.getenv("WHOISXML_API_KEY")
    if not api_key:
        print("Set WHOISXML_API_KEY in env.", file=sys.stderr)
        sys.exit(1)

    # Resolve A/AAAA
    dns_records = resolve_ips(domain)
    ips = sorted(set(dns_records["A"] + dns_records["AAAA"]))

    result: Dict[str, Any] = {
        "input_domain": domain,
        "dns": dns_records,
        "lookups": [],
        "domain_lookup_used": False,
    }

    if ips:
        for ip in ips:
            try:
                payload = geo_lookup_ip(api_key, ip, reverse_ip=True)
                result["lookups"].append(summarize_payload(payload))
            except requests.HTTPError as e:
                result["lookups"].append({"ip": ip, "error": f"HTTP {e.response.status_code}", "raw": e.response.text[:400]})
            except Exception as e:
                result["lookups"].append({"ip": ip, "error": str(e)})
    else:
        # Fall back to domain‑based lookup (API resolves internally)
        try:
            payload = geo_lookup_domain(api_key, domain)
            row = summarize_payload(payload)
            row["note"] = "domain-based lookup"
            result["domain_lookup_used"] = True
            result["lookups"].append(row)
        except Exception as e:
            result["lookups"].append({"domain": domain, "error": str(e)})

    print(json.dumps(result, indent=2))

IPINFO_BASE = "https://ipinfo.io"  # requires token for reliable JSON

def ipinfo_lookup(ip: str) -> dict:
    token = os.getenv("IPINFO_TOKEN")
    if not token:
        return {"error": "IPINFO_TOKEN not set"}
    r = requests.get(f"{IPINFO_BASE}/{ip}/json", params={"token": token}, timeout=10)
    r.raise_for_status()
    j = r.json()
    # j.get("loc") is "lat,lon"
    lat, lon = (None, None)
    if isinstance(j.get("loc"), str) and "," in j["loc"]:
        lat_s, lon_s = j["loc"].split(",", 1)
        try:
            lat, lon = float(lat_s), float(lon_s)
        except ValueError:
            pass
    return {
        "ip": ip,
        "country": j.get("country"),
        "region": j.get("region"),
        "city": j.get("city"),
        "lat": lat,
        "lon": lon,
        "asn": j.get("asn", {}).get("asn") if isinstance(j.get("asn"), dict) else None,
        "as_org": j.get("asn", {}).get("name") if isinstance(j.get("asn"), dict) else None,
        "org": j.get("org"),
        "raw": j,
    }

def compare_geo(a: dict, b: dict) -> dict:
    def norm(x): return (x or "").strip().upper()
    diff = {}
    for k in ("country", "region", "city"):
        if norm(a.get(k)) and norm(b.get(k)) and norm(a.get(k)) != norm(b.get(k)):
            diff[k] = {"whoisxml": a.get(k), "ipinfo": b.get(k)}
    return diff


ip = "176.32.230.47"
payload = geo_lookup_ip("at_H683qthY463FTlZVWh92vJVBTl34D", ip, reverse_ip=True)
wx = summarize_payload(payload)
ipinfo = ipinfo_lookup(ip)
diff = compare_geo(wx, ipinfo) if "error" not in ipinfo else {}

result["lookups"].append({
    "ip": ip,
    "providers": {
        "whoisxml": wx,
        "ipinfo": ipinfo,
    },
    "discrepancies": diff,
    "rdns": socket.getfqdn(ip)
})
