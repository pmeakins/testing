from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from pathlib import Path
from bs4 import BeautifulSoup
import yaml, random, os, requests, time, re, html


NUMVERIFY_URL = os.getenv("NUMVERIFY_BASE_URL", "https://apilayer.net/api/validate")
API_KEY = os.getenv("NUMVERIFY_API_KEY")

@require_POST
def validate_number(request):
    if not API_KEY:
        return HttpResponse('<div class="p-3 rounded bg-red-50 border border-red-200">API key missing</div>', status=500)

    raw = request.POST.get("number", "")
    country_code = request.POST.get("country_code", "")  # optional: "GB", "US", etc.

    # tidy input: keep digits and leading +
    number = re.sub(r"[^\d+]", "", raw)

    try:
        r = requests.get(NUMVERIFY_URL, params={
            "access_key": API_KEY,
            "number": number,
            "country_code": country_code,
            "format": 1
        }, timeout=6)
        data = r.json()
    except Exception:
        return HttpResponse('<div class="p-3 rounded bg-red-50 border border-red-200">Lookup failed</div>', status=502)

    # Numverify error shape: {"success": false, "error": {...}}
    if data.get("success") is False:
        info = (data.get("error") or {}).get("info", "API error")
        return HttpResponse(f'<div class="p-3 rounded bg-red-50 border border-red-200">{info}</div>', status=400)

    valid = data.get("valid", False)
    local_format = data.get("local_format") or data.get("number") or number
    intl_format = data.get("intl_format") or data.get("number") or number
    country_code = data.get("country_code") or data.get("country_code") or ""
    country_name = data.get("country_name") or data.get("country_name") or ""

    location = data.get("location") or "Unknown"
    carrier = data.get("carrier") or "Unknown"
    line_type = data.get("line_type") or "Unknown"

    html = [
    f"<div class='font-semibold'>{'Valid' if valid else 'Invalid/Unknown'} number</div>",
]

    if local_format:
        html.append(f"<div>Local Format: {local_format}</div>")
    if intl_format:
        html.append(f"<div>International Format: {intl_format}</div>")
    if country_code:
        html.append(f"<div>Country Code: {country_code}</div>")
    if country_name:
        html.append(f"<div>Country Name: {country_name}</div>")
    if location:
        html.append(f"<div>Location: {location}</div>")

    html.append(f"<div>Carrier: {carrier}</div>")
    html.append(f"<div>Line Type: {line_type}</div>")

    html = f"""
    <div class="p-3 rounded {'bg-green-50 border border-green-200' if valid else 'bg-yellow-50 border border-yellow-200'}">
    {''.join(html)}
    </div>
    """
    return HttpResponse(html)

#  End of phone validation

#  Start of fraud score
#  End of fraud score


@require_POST
def show_date(request):
    # Grab everything that was submitted
    posted_data = dict(request.POST)
    # Format into a simple string: key=value
    posted_items = "<br>".join([f"{k}: {', '.join(v)}" for k, v in posted_data.items() if k != "csrfmiddlewaretoken"])

    # Current server date/time
    # date_str = now().strftime("%Y-%m-%d %H:%M:%S")

    # Build the HTML fragment
    return HttpResponse(
        f'<div class="p-3 rounded bg-green-100 border">'
        # f'<strong>Server date/time:</strong> {date_str}<br>'
        f'<strong>Form data received:</strong><br>{posted_items}'
        f'</div>'
    )

def base(request):
    yaml_path = Path(settings.BASE_DIR) / settings.ACTIVE_APP / "static" / "data" / "alerts.yaml"

    alerts = []
    error = None

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
            if isinstance(data, dict) and "alerts" in data:
                alerts = data["alerts"]
            elif isinstance(data, list):
                alerts = data
        alerts = [str(x).strip() for x in alerts if str(x).strip()]
        random.shuffle(alerts)  # <- Shuffle the list in place
    except FileNotFoundError:
        error = "[alerts.yaml missing]"
    except yaml.YAMLError as e:
        error = f"[YAML error: {e}]"

    return render(request, "base/base.html", {"alerts": alerts, "alerts_error": error})



ABSTRACT_URL = os.getenv("ABSTRACT_EMAIL_BASE_URL", "https://emailreputation.abstractapi.com/v1/")
ABSTRACT_KEY = os.getenv("ABSTRACT_EMAIL_API_KEY")

def _flatten(obj, prefix=""):
    """Flatten dict/list into dotted key:value pairs."""
    rows = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            rows.extend(_flatten(v, f"{prefix}{k}." if prefix else f"{k}."))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            rows.extend(_flatten(v, f"{prefix}{i}."))
    else:
        key = prefix[:-1] if prefix.endswith(".") else prefix
        rows.append((key, obj))
    return rows

def _fmt(v):
    if v is True: return "true"
    if v is False: return "false"
    if v is None: return "null"
    return str(v)


@require_POST
def validate_email(request):
    if not ABSTRACT_KEY:
        return HttpResponse(
            '<div class="p-3 rounded bg-red-50 border border-red-200">Missing AbstractAPI key</div>', status=500
        )

    email = (request.POST.get("email") or "").strip()
    if not email:
        return HttpResponse(
            '<div class="p-3 rounded bg-yellow-50 border border-yellow-200">Please provide an email</div>', status=400
        )

    try:

        r = requests.get(
            ABSTRACT_URL,
            params={"api_key": ABSTRACT_KEY, "email": email},
            timeout=8,
        )

        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        return HttpResponse(
            f'<div class="p-3 rounded bg-red-50 border border-red-200">Lookup failed: {html.escape(str(e))}</div>',
            status=502,
        )
    except ValueError:
        return HttpResponse(
            '<div class="p-3 rounded bg-red-50 border border-red-200">Invalid JSON from API</div>', status=502
        )

    # Build rows
    rows = _flatten(data)
    if not rows:
        rows = [("result", "No data")]

    # Nice header chip (if AbstractAPI returns a quality score or deliverability)
    quality = data.get("quality_score")
    deliverability = data.get("deliverability")
    badge = ""
    if deliverability:
        color = {
            "DELIVERABLE": "bg-green-100 text-green-800 border-green-200",
            "RISKY": "bg-yellow-100 text-yellow-800 border-yellow-200",
            "UNDELIVERABLE": "bg-red-100 text-red-800 border-red-200",
        }.get(str(deliverability).upper(), "bg-gray-100 text-gray-800 border-gray-200")
        badge = f"""
        <div class="mb-2 inline-block rounded border px-2 py-1 text-xs {color}">
          Deliverability: {html.escape(str(deliverability))}
          {' · Quality: ' + html.escape(str(quality)) if quality is not None else ''}
        </div>
        """

    # Render HTML table fragment
    table_rows = "\n".join(
        f"<tr><th class='text-left align-top p-2 bg-gray-50 border'>{html.escape(str(k))}</th>"
        f"<td class='p-2 border'>{html.escape(_fmt(v))}</td></tr>"
        for k, v in rows
    )
    html_fragment = f"""
<div class="p-3 rounded border bg-white">
  <div class="mb-2 font-semibold">Email check for: <code>{html.escape(email)}</code></div>
  {badge}
  <div class="overflow-auto">
    <table class="min-w-full border border-collapse text-sm">
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>
</div>
"""
    return HttpResponse(html_fragment)


