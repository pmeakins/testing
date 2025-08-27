from django.urls import path
from . import views

urlpatterns = [
    path('', views.base, name='base'),
    path("validate_number/", views.validate_number, name="validate_number"),
    path("validate-email/", views.validate_email, name="validate_email"),
]

