from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from .models import Report
from .forms import SearchForm

def home(request):
    return render(request, 'home.html')

def search_report(request):
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone_number']
            reports = Report.objects.filter(phone_number=phone)
            if reports.exists():
                # Display cached reports
                return render(request, 'results.html', {'reports': reports, 'phone': phone})
            else:
                # Simulate new report creation (in production, use Celery for async)
                new_report = Report(phone_number=phone, description=form.cleaned_data.get('description', ''), trust_score=50)  # Mock score
                new_report.save()
                # Send email (configure settings.EMAIL_HOST etc. in settings.py)
                send_mail(
                    'Your Scam Registry Report',
                    f'Report for {phone} is ready. Trust Score: {new_report.trust_score}',
                    settings.DEFAULT_FROM_EMAIL,
                    [form.cleaned_data['email']],
                )
                return redirect('results', phone=phone)  # Or a waiting page
    else:
        form = SearchForm()
    return render(request, 'search.html', {'form': form})
