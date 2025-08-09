from django.urls import path
from . import views  # relative import to avoid conflicts

urlpatterns = [
    path('', views.home, name='home'),
]
