
from django.contrib import admin
from django.conf import settings
from django.urls import path, include, re_path
from django.shortcuts import redirect
from django.views.defaults import page_not_found
from django.http import HttpResponse

urlpatterns = [
#    path('admin/', admin.site.urls),
    path('', include('v1.urls')),
]

def silent_404(request, exception=None):
    # Don’t interfere with static and media
    if request.path.startswith(settings.STATIC_URL):
        return page_not_found(request, exception)
    if getattr(settings, "MEDIA_URL", None) and request.path.startswith(settings.MEDIA_URL):
        return page_not_found(request, exception)

    # For normal page requests, give your "silent" 204
    accept = request.headers.get("Accept", "")
    if "text/html" in accept:
        return HttpResponse(status=204)

    # For APIs or anything else, fallback to Django’s default 404
    return page_not_found(request, exception)


handler404 = silent_404

