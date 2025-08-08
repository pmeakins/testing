# website/views.py
from django.shortcuts import render

def home(request):
    return render(request, "website/home.html")
