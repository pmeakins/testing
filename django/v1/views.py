from django.shortcuts import render
from django.conf import settings
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import time, random
import yaml
import random


import random  # Add this import

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
