from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('article/new/', views.article_new, name='article_new'),
]
