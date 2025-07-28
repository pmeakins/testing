from django.contrib import admin
from django.urls import path
from registry import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('search/', views.search_report, name='search'),
]
