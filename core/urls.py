"""Rotas para o app core."""
from django.urls import path

from .views import health_check, home, summary_detail

app_name = "core"

urlpatterns = [
    path("", home, name="home"),
    path("resumo/<slug:card>/", summary_detail, name="summary_detail"),
    path("health/", health_check, name="health-check"),
]
