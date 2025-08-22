from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.views.defaults import page_not_found
from django.http import HttpResponse

urlpatterns = [
    path("", include("v1.urls")),
]
from django.conf import settings
from django.views.defaults import page_not_found
from django.http import HttpResponse

def silent_404(request, exception=None):
    # let static use normal 404 handling (or be served if it exists)
    if request.path.startswith(settings.STATIC_URL):
        print(request.path.startswith(settings.STATIC_URL))
        return page_not_found(request, exception)
    return HttpResponse(status=204)

handler404 = silent_404

