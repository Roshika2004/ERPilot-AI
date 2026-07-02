from django.urls import path
from .views import create_claim

urlpatterns = [
    path('create/', create_claim, name='create_claim'),
]