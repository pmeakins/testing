#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ScamAdvisory — Email domain diagnostics with risk scoring + reputation checks.

Adds:
- DNSBL lookups (Spamhaus ZEN, SpamCop) for first A-record IP
- AbuseIPDB (optional key)
- IPQualityScore IP reputation (optional key)

Keys can be passed with CLI flags or env vars ABUSEIPDB_KEY / IPQS_KEY.

Usage:
  python email_diags.py user@example.com
  python email_diags.py user@example.com --verbose --abuseipdb-key ... --ipqs-key ...
"""

import argparse, json, os, socket, ssl
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import dns.resolver
import requests
import whois

# ----------------------------- Configuration -----------------------------

TIMEOUT = 6
UA = "ScamAdvisoryEmailDiag/1.1 (+https://scamadvisory.co.uk)"

# Geo risk configuration (ISO-3166-1 alpha-2 codes)
GEO_RISK = {
    "HIGH":   {"CN", "RU", "BY", "IR", "KP"},
    "MEDIUM": {"TR", "VN", "ID", "NG", "PK", "BR"},
    "IMPACT_HIGH": 40,
    "IMPACT_MEDIUM": 25,
    "NON_GB_ELEVATE_TO_MEDIUM": True,
    "NON_GB_NUDGE_IMPACT": 5,
}

# Reputation providers: enable/disable and weights
REPUTATION_CFG = {
    "DNSBL": {
        "ENABLED": True,
        "ZONES": [
            # order matters (we report first match with its weight)
            ("zen.spamhaus.org", 60),  # very authoritative
            ("bl.spamcop.net",   40),
        ],
    },
    "ABUSEIPDB": {"ENABLED": True},  # needs key
    "IPQS":      {"ENABLED": True},  # needs key
}

REPUTATION_WEIGHTS = {
    # AbuseIPDB: impact = min(confidence * 0.5, 50)
    "ABUSEIPDB_MULTIPLIER": 0.5,
    "ABUSEIPDB_CAP": 50,

    # IPQS: impact = min(fraud_score * 0.4, 40)
    "IPQS_MULTIPLIER": 0.4,
    "IPQS_CAP": 40,
}

# ----------------------------- Helpers -----------------------------

def to_iso(dt) -> Optional[str]:
    if isinstance(dt, list) and dt:
        dt = dt[0]
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    if isinstance(dt, str):
        return dt
    return None

def parse_iso_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            return None

def domain_from_email(email: str) -> str:
    if "@" not in email:
        raise ValueError("Provide an email like name@example.com")
    return email.split("@", 1)[1].strip().lower()

def whois_domain_min(domain: str) -> Dict[str, Any]:
    try:
        w = whois.whois(domain)
        domain_name = w.domain_name[0] if isinstance(w.domain_name, list) else w.domain_name
        return {
            "domain_name": domain_name,
            "registrar": w.registrar,
            "creation_date": to_iso(w.creation_date),
            "expiration_date": to_iso(w.expiration_date),
        }
    except Exception as e:
        return {"error": f"domain whois failed: {e.__class__.__name__}: {e}"}

def resolve_A(domain: str) -> List[str]:
    try:
        r = dns.resolver.Resolver()
        r.timeout = r.lifetime = TIMEOUT
        return [a.to_text() for a in r.resolve(domain, "A")]
    except Exception:
        return []

def ip_geo_min(ip: str) -> Dict[str, Any]:
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,message,country,countryCode,regionName,city,lat,lon,isp,org"},
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        )
        j = r.json()
        if j.get("status") != "success":
            return {"error": f"geo failed: {j.get('message')}"}
        return {
            "country": j.get("country"),
            "countryCode": j.get("countryCode"),
            "region": j.get("regionName"),
            "city": j.get("city"),
            "lat": j.get("lat"),
            "lon": j.get("lon"),
            "isp": j.get("isp"),
            "org": j.get("org"),
        }
    except Exception as e:
        return {"error": f"geo failed: {e.__class__.__name__}: {e}"}

def parse_name_tuple_list(tuples: List[tuple]) -> Dict[str, str]:
    out = {}
    for k, v in tuples:
        out[k] = v
    return out

def parse_cert_min(cert: Dict[str, Any]) -> Dict[str, Any]:
    issuer = {}
    for rdn in cert.get("issuer", []) or []:
        issuer.update(parse_name_tuple_list(rdn))
    subject = {}
    for rdn in cert.get("subject", []) or []:
        subject.update(parse_name_tuple_list(rdn))

    not_after = cert.get("notAfter")
    def parse_dt(s):
        try:
            return datetime.strptime(s, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            return s

    issuer_cn = issuer.get("commonName")
    issuer_o  = issuer.get("organizationName")
    is_le = ("Let's Encrypt" in (issuer_cn or "")) or ("Let's Encrypt" in (issuer_o or ""))
    is_self = bool(subject and issuer and subject == issuer)

    return {
        "issuer": {
            "countryName": issuer.get("countryName"),
            "organizationName": issuer_o,
            "commonName": issuer_cn,
            "not_after": parse_dt(not_after) if not_after else None,
            "is_self_signed": is_self,
            "issuer_summary": issuer_cn or issuer_o,
            "is_lets_encrypt": is_le,
        }
    }

def tls_probe(host: str, port: int = 443) -> Dict[str, Any]:
    out = {"ssl": {"tls_valid": False}}
    # Verified first
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                out["ssl"]["tls_valid"] = True
                cert = ssock.getpeercert()
                out.update(parse_cert_min(cert))
                return out
    except Exception:
        pass
    # Fallback: unverified (still get issuer data)
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                out.update(parse_cert_min(cert))
    except Exception:
        pass
    return out

# ----------------------------- Reputation Providers -----------------------------

def dnsbl_lookup(ip: str, zones: List[tuple]) -> List[Dict[str, Any]]:
    """Query DNSBL zones for a single IPv4 address. Returns list of hits."""
    hits = []
    try:
        octs = ip.split(".")
        if len(octs) != 4:
            return hits
        reversed_ip = ".".join(reversed(octs))
        r = dns.resolver.Resolver()
        r.timeout = r.lifetime = TIMEOUT

        for zone, weight in zones:
            qname = f"{reversed_ip}.{zone}"
            try:
                # listed if A record exists
                r.resolve(qname, "A")
                # optional TXT detail
                txt = []
                try:
                    txt = [t.to_text().strip('"') for t in r.resolve(qname, "TXT")]
                except Exception:
                    pass
                hits.append({"zone": zone, "weight": weight, "txt": txt})
                # stop at first match (strongest first in list)
                break
            except Exception:
                continue
    except Exception:
        pass
    return hits

def abuseipdb_check(ip: str, api_key: Optional[str]) -> Optional[Dict[str, Any]]:
    if not api_key:
        return None
    try:
        r = requests.get(
            "https://api.abuseipdb.com/api/v2/check",
            headers={"Key": api_key, "Accept": "application/json", "User-Agent": UA},
            params={"ipAddress": ip, "maxAgeInDays": 365},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return {"error": f"abuseipdb status {r.status_code}", "body": r.text[:200]}
        data = r.json().get("data", {})
        # confidence_score is 0-100
        return {"confidence_score": data.get("abuseConfidenceScore"), "total_reports": data.get("totalReports")}
    except Exception as e:
        return {"error": f"abuseipdb failed: {e.__class__.__name__}: {e}"}

def ipqs_ip_check(ip: str, api_key: Optional[str]) -> Optional[Dict[str, Any]]:
    if not api_key:
        return None
    try:
        r = requests.get(
            f"https://ipqualityscore.com/api/json/ip/{api_key}/{ip}",
            params={"strictness": 1, "allow_public_access_points": "true"},
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return {"error": f"ipqs status {r.status_code}", "body": r.text[:200]}
        j = r.json()
        # fraud_score is 0-100
        return {
            "fraud_score": j.get("fraud_score"),
            "proxy": j.get("proxy"),
            "vpn": j.get("vpn"),
            "tor": j.get("tor"),
            "recent_abuse": j.get("recent_abuse"),
        }
    except Exception as e:
        return {"error": f"ipqs failed: {e.__class__.__name__}: {e}"}

# ----------------------------- Risk Scoring -----------------------------

def compute_risk(whois_min: Dict[str, Any], ssl_min: Dict[str, Any], ip_details: List[Dict[str, Any]],
                 rep: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns: {"risk_score": int(0-100), "risk_label": str, "signals": list}
    Factors: Domain age, SSL (validity, LE, self-signed), GEO (country), Reputation (DNSBL, AbuseIPDB, IPQS)
    """
    score = 0
    signals = []

    # ----- Domain Age -----
    creation_iso = whois_min.get("creation_date")
    created_dt = parse_iso_date(creation_iso) if creation_iso else None
    now = datetime.now(timezone.utc)

    if not created_dt:
        score += 10; signals.append({"signal": "missing_creation_date", "impact": +10})
        age_days = None
    else:
        age_days = (now - created_dt).days
        if age_days < 7:
            score += 40; signals.append({"signal": "age_<7d", "impact": +40, "age_days": age_days})
        elif age_days < 90:
            score += 25; signals.append({"signal": "age_7d_to_3m", "impact": +25, "age_days": age_days})
        elif age_days < 180:
            score += 12; signals.append({"signal": "age_3m_to_6m", "impact": +12, "age_days": age_days})
        elif age_days < 365:
            score += 5;  signals.append({"signal": "age_6m_to_12m", "impact": +5, "age_days": age_days})
        else:
            score -= 15; signals.append({"signal": "age_>12m", "impact": -15, "age_days": age_days})

    # ----- SSL -----
    tls_valid = ssl_min.get("ssl", {}).get("tls_valid", False)
    issuer = ssl_min.get("issuer", {}) if "issuer" in ssl_min else {}
    is_self = bool(issuer.get("is_self_signed"))
    is_le = bool(issuer.get("is_lets_encrypt"))

    if not tls_valid:
        score += 40; signals.append({"signal": "tls_invalid_or_absent", "impact": +40})
    else:
        if not is_le:
            score -= 10; signals.append({"signal": "tls_valid_non_LE", "impact": -10})

    if is_self:
        score += 30; signals.append({"signal": "self_signed", "impact": +30})

    if is_le:
        le_impact = 45
        if created_dt and (now - created_dt).days < 90:
            le_impact += 10
        score += le_impact
        signals.append({"signal": "lets_encrypt", "impact": le_impact})

    # ----- GEO (first IP only) -----
    country_code = None
    if ip_details and isinstance(ip_details[0].get("geo"), dict):
        country_code = ip_details[0]["geo"].get("countryCode")

    if country_code is None:
        score += 5; signals.append({"signal": "geo_unknown", "impact": +5})
    else:
        if country_code in GEO_RISK["HIGH"]:
            imp = GEO_RISK["IMPACT_HIGH"]; score += imp
            signals.append({"signal": f"geo_high:{country_code}", "impact": +imp})
        elif country_code in GEO_RISK["MEDIUM"]:
            imp = GEO_RISK["IMPACT_MEDIUM"]; score += imp
            signals.append({"signal": f"geo_medium:{country_code}", "impact": +imp})
        elif country_code != "GB":
            tmp = max(0, min(100, score))
            label = "Low" if tmp < 25 else ("Medium" if tmp < 50 else ("High" if tmp < 75 else "Critical"))
            if GEO_RISK["NON_GB_ELEVATE_TO_MEDIUM"] and label == "Low":
                delta = max(0, 25 - tmp); score += delta
                signals.append({"signal": f"geo_non_gb_elevate:{country_code}", "impact": +delta})
            else:
                nudge = GEO_RISK["NON_GB_NUDGE_IMPACT"]
                if nudge: score += nudge; signals.append({"signal": f"geo_non_gb_nudge:{country_code}", "impact": +nudge})

    # ----- REPUTATION (first IP only) -----
    ip = ip_details[0]["ip"] if ip_details else None
    if ip:
        # DNSBL
        dnsbl_hits = rep.get("dnsbl_hits") or []
        if dnsbl_hits:
            h = dnsbl_hits[0]  # first/strongest only
            score += h["weight"]
            signals.append({"signal": f"dnsbl_listed:{h['zone']}", "impact": +h["weight"], "txt": h.get("txt")})

        # AbuseIPDB
        a = rep.get("abuseipdb")
        if isinstance(a, dict) and "confidence_score" in a and isinstance(a["confidence_score"], (int, float)):
            impact = min(a["confidence_score"] * REPUTATION_WEIGHTS["ABUSEIPDB_MULTIPLIER"], REPUTATION_WEIGHTS["ABUSEIPDB_CAP"])
            score += impact
            signals.append({"signal": "abuseipdb_confidence", "impact": +impact, "confidence": a["confidence_score"]})

        # IPQS
        q = rep.get("ipqs")
        if isinstance(q, dict) and "fraud_score" in q and isinstance(q["fraud_score"], (int, float)):
            impact = min(q["fraud_score"] * REPUTATION_WEIGHTS["IPQS_MULTIPLIER"], REPUTATION_WEIGHTS["IPQS_CAP"])
            score += impact
            signals.append({"signal": "ipqs_fraud_score", "impact": +impact, "fraud_score": q["fraud_score"]})

    # ----- Clamp & Label -----
    score = max(0, min(100, int(round(score))))
    if score >= 75:
        label = "Critical"
    elif score >= 50:
        label = "High"
    elif score >= 25:
        label = "Medium"
    else:
        label = "Low"

    return {"risk_score": score, "risk_label": label, "signals": signals}

# ----------------------------- Main diag -----------------------------

def diag(email: str, verbose: bool, abuseipdb_key: Optional[str], ipqs_key: Optional[str]) -> Dict[str, Any]:
    domain = domain_from_email(email)
    whois_min = whois_domain_min(domain)

    A = resolve_A(domain)
    probe_host = domain if A else f"www.{domain}"
    ssl_min = tls_probe(probe_host)

    ip_details = []
    if A:
        ip = A[0]
        ip_geo = ip_geo_min(ip)
        ip_details.append({"ip": ip, "geo": ip_geo})

    # Reputation checks (first IP only)
    rep = {}
    if ip_details:
        ip = ip_details[0]["ip"]

        # DNSBL
        if REPUTATION_CFG["DNSBL"]["ENABLED"]:
            rep["dnsbl_hits"] = dnsbl_lookup(ip, REPUTATION_CFG["DNSBL"]["ZONES"])

        # AbuseIPDB
        if REPUTATION_CFG["ABUSEIPDB"]["ENABLED"]:
            rep["abuseipdb"] = abuseipdb_check(ip, abuseipdb_key)

        # IPQS
        if REPUTATION_CFG["IPQS"]["ENABLED"]:
            rep["ipqs"] = ipqs_ip_check(ip, ipqs_key)

    minimal = {
        "input_email": email,
        "domain": domain,
        "domain_whois": whois_min,
        **ssl_min,            # {"ssl": {...}, "issuer": {...}}
        "ip_details": ip_details,
        "reputation": rep,
    }

    minimal.update(compute_risk(whois_min, ssl_min, ip_details, rep))

    if not verbose:
        return minimal

    # ---- VERBOSE EXTRAS ----
    verbose_blob: Dict[str, Any] = {}
    r = dns.resolver.Resolver(); r.timeout = r.lifetime = TIMEOUT

    def safe_resolve(name, rtype):
        try:
            return [x.to_text() for x in r.resolve(name, rtype)]
        except Exception:
            return []

    verbose_blob["dns"] = {
        "A": A,
        "AAAA": safe_resolve(domain, "AAAA"),
        "MX": [
            {"preference": rr.preference, "host": str(rr.exchange).rstrip(".")}
            for rr in (r.resolve(domain, "MX") if safe_resolve(domain, "MX") else [])
        ],
    }

    try:
        full_w = whois.whois(domain)
        verbose_blob["domain_whois_full"] = {k: (v if k != "text" else None) for k, v in full_w.__dict__.items()}
    except Exception as e:
        verbose_blob["domain_whois_full_error"] = str(e)

    return {**minimal, **verbose_blob}

# ----------------------------- CLI -----------------------------

def main():
    ap = argparse.ArgumentParser(description="ScamAdvisory Email Diagnostics + Reputation scoring.")
    ap.add_argument("email", help="Email to check, e.g. user@example.com")
    ap.add_argument("--verbose", action="store_true", help="Include DNS details and extended WHOIS")
    ap.add_argument("--abuseipdb-key", default=os.getenv("ABUSEIPDB_KEY"), help="AbuseIPDB API key (or env ABUSEIPDB_KEY)")
    ap.add_argument("--ipqs-key", default=os.getenv("IPQS_KEY"), help="IPQualityScore API key (or env IPQS_KEY)")
    args = ap.parse_args()

    data = diag(args.email, verbose=args.verbose, abuseipdb_key=args.abuseipdb_key, ipqs_key=args.ipqs_key)
    print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

