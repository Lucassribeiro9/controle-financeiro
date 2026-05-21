"""Rotas para o app rates."""

from django.urls import path

from . import views

app_name = "rates"

urlpatterns = [
    path("rates/", views.rates_page, name="list"),
    path("rates/create/", views.reference_rate_create_page, name="create"),
    path("rates/yields/create/", views.yield_config_create_page, name="yield-config-create"),
    path(
        "rates/yields/<int:config_id>/edit/",
        views.yield_config_update_page,
        name="yield-config-edit",
    ),
    path("rates/simulate/", views.yield_simulation_page, name="simulate"),
]
