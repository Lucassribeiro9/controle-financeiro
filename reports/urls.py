"""Rotas para o app reports."""

from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path(
        "reports/month/<int:year>/<int:month>/",
        views.monthly_dashboard,
        name="monthly-dashboard",
    ),
]
