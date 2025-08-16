from django.shortcuts import render
from django.conf import settings
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import time, random











def base(request):
    logical_path = f"{settings.ACTIVE_APP}/static/data/alert.txt"
    text_file_path = Path(logical_path)
    try:
        with open(text_file_path, "r", encoding="utf-8") as f:
            report_text = f.read()
    except FileNotFoundError:
        report_text = "[Report text file missing]"

    # leaderboard_data = fetch_leaderboard()

    # return render(request, "base/base.html", {"report_text": report_text}, {"leaderboard_data": leaderboard_data})
    return render(request, "base/base.html", {"report_text": report_text})