#!/usr/bin/env python3
import csv
import io
import os
import re
from typing import List, Dict, Iterable
from flask import Flask, Response, abort, request

app = Flask(__name__)

# --- Configure paths (override with env vars if you like) ---
COUNTRY_CSV_PATH = os.getenv("COUNTRY_CSV_PATH", "countrycode.csv")
NUM_CSV_PATH = os.getenv("NUM_CSV_PATH", "num.csv")

# --- Normalization helpers ---
def normalize_code(value: str) -> str:
    """
    Normalize phone codes or numbers for matching:
    - strip leading '+' or '00'
    - keep digits only
    """
    if value is None:
        return ""
    v = value.strip()
    if v.startswith("+"):
        v = v[1:]
    elif v.startswith("00"):
        v = v[2:]
    # Keep digits only
    return re.sub(r"\D", "", v)

def read_csv_rows(path: str, delimiter: str) -> Iterable[Dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            yield row

def to_csv(rows: List[Dict[str, str]], header_order: List[str]) -> str:
    """Render rows to CSV text preserving header order."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header_order)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in header_order})
    return buf.getvalue()

# --- Route 1: country code lookup (match against 2nd column) ---
# Input examples: /countrycode/+44  or /countrycode/44  or /countrycode/0044
@app.get("/countrycode/<code>")
def countrycode_lookup(code: str):
    # countrycode.csv headings (per your sample):
    # Country Name,Phone Code,Continent,Capital,Time Zone in Capital,Currency,Languages
    matches: List[Dict[str, str]] = []
    wanted = normalize_code(code)

    try:
        rows = list(read_csv_rows(COUNTRY_CSV_PATH, delimiter=","))  # comma-separated
    except FileNotFoundError:
        abort(404, description=f"country CSV not found at {COUNTRY_CSV_PATH}")

    if not rows:
        abort(404, description="country CSV is empty")

    headers = list(rows[0].keys())  # preserve order
    phone_code_col = "Phone Code"  # 2nd element
    if phone_code_col not in headers:
        abort(400, description=f"'Phone Code' column not found in {COUNTRY_CSV_PATH}")

    for r in rows:
        # normalize value in the 2nd column (may include hyphens like 1-684)
        code_norm = normalize_code(r.get(phone_code_col, ""))
        if code_norm == wanted:
            matches.append(r)

    if not matches:
        abort(404, description=f"No match for code '{code}'")

    csv_text = to_csv(matches, headers)
    return Response(csv_text, mimetype="text/csv")

# --- Route 2: num lookup (match against 1st column) ---
# Input examples: /num/+4478778745359  or /num/4478778745359  or /num/004478778745359
@app.get("/num/<number>")
def number_lookup(number: str):
    # num.csv headings (per your sample, semicolon separated):
    # PhoneNumber;Score;Ratings;Country;Area Code;Search Requests;CallerType;NameCompany;PrefixName;Deeplink;CallerTypeId
    matches: List[Dict[str, str]] = []
    wanted = normalize_code(number)

    try:
        rows = list(read_csv_rows(NUM_CSV_PATH, delimiter=";"))  # semicolon-separated
    except FileNotFoundError:
        abort(404, description=f"num CSV not found at {NUM_CSV_PATH}")

    if not rows:
        abort(404, description="num CSV is empty")

    headers = list(rows[0].keys())  # preserve order
    phone_col = "PhoneNumber"  # 1st element
    if phone_col not in headers:
        abort(400, description=f"'PhoneNumber' column not found in {NUM_CSV_PATH}")

    for r in rows:
        num_norm = normalize_code(r.get(phone_col, ""))
        if num_norm == wanted:
            matches.append(r)

    if not matches:
        abort(404, description=f"No match for number '{number}'")

    csv_text = to_csv(matches, headers)
    return Response(csv_text, mimetype="text/csv")

# --- Convenience: show where to PUT the files / how to call routes ---
@app.get("/routes")
def routes_info():
    return {
        "country_csv_path": os.path.abspath(COUNTRY_CSV_PATH),
        "num_csv_path": os.path.abspath(NUM_CSV_PATH),
        "routes": {
            "countrycode_lookup": "/countrycode/<code>  (code like +44 | 44 | 0044)",
            "number_lookup": "/num/<number>            (number like +447..., 447..., or 00447...)",
        },
        "notes": [
            "countrycode.csv must be comma-separated with a 'Phone Code' column.",
            "num.csv must be semicolon-separated with a 'PhoneNumber' column.",
            "Matching is exact after normalization (strip +/00 and non-digits).",
        ],
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

