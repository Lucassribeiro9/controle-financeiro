"""Rotas para o app cards."""

from django.urls import path

from . import views

app_name = "cards"

urlpatterns = [
    path("cards/", views.card_list_page, name="list"),
    path("cards/create/", views.card_create_page, name="create"),
    path("cards/<int:card_id>/edit/", views.card_update_page, name="update"),
    path("cards/statements/", views.statement_list_page, name="statements"),
    path(
        "cards/statements/<int:statement_id>/",
        views.statement_detail_page,
        name="statement-detail",
    ),
    path(
        "cards/statements/<int:statement_id>/pay/",
        views.pay_statement_page,
        name="pay-statement",
    ),
]
