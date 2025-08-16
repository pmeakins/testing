
from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from django.http import HttpResponse

urlpatterns = [
#    path('admin/', admin.site.urls),
    path('', include('v1.urls')),
]

def silent_404(request, exception=None):
    # Fast, empty response — avoids redirects or template rendering
    return HttpResponse(status=204)

handler404 = silent_404


