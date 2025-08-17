from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.views.defaults import page_not_found
from django.http import HttpResponse

urlpatterns = [
    path("", include("v1.urls")),
]

# Serve collected files from STATIC_ROOT at /static/
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


def silent_404(request, exception=None):
    if not request.path.startswith("/static/"):
        # print(request.path.startswith(settings.STATIC_URL))
        if request.path.startswith(settings.STATIC_URL):
            return page_not_found(request, exception)
        return HttpResponse(status=204)

handler404 = silent_404
