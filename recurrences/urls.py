"""Rotas para o app recurrences."""

from django.urls import path

from . import views

app_name = "recurrences"

urlpatterns = [
    path(
        "recurrences/month/<int:year>/<int:month>/",
        views.monthly_forecasts,
        name="monthly-forecasts",
    ),
    path(
        "recurrences/forecasts/<int:transaction_id>/confirm/",
        views.confirm_forecast,
        name="confirm-forecast",
    ),
    path(
        "recurrences/forecasts/<int:transaction_id>/ignore/",
        views.ignore_forecast,
        name="ignore-forecast",
    ),
    path(
        "recurrences/forecasts/<int:transaction_id>/adjust/",
        views.adjust_forecast,
        name="adjust-forecast",
    ),
]
