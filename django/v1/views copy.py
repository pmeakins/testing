from django.shortcuts import render
from django.conf import settings
from django.contrib.staticfiles import finders
from django.shortcuts import render
from pathlib import Path

# def base(request):
#     return render(request, 'base/base.html')

def read_alert_text(file):
    # looks for <ACTIVE_APP>/data/alert.txt inside that app's static dir
    logical_path = f"{settings.ACTIVE_APP}/data/{file})"
    file_path = finders.find(logical_path)  # absolute path or None

    if not file_path:
        return "[Alert text file missing]"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[Error reading alert text: {e}]"


def base(request):
    alert_text = read_alert_text("alert.txt")
    return render(request, "base/base.html", {"alert_text": alert_text})
