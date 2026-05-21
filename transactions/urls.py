"""Rotas para o app transactions."""

from django.urls import path

from . import views

app_name = "transactions"

urlpatterns = [
    path("transactions/", views.transaction_list_page, name="list"),
    path("transactions/create/", views.transaction_create_page, name="create"),
    path("transactions/transfers/", views.transfer_list_page, name="transfers"),
    path(
        "transactions/transfers/create/",
        views.transfer_create_page,
        name="transfer-create",
    ),
    path(
        "transactions/<int:transaction_id>/",
        views.transaction_detail_page,
        name="detail",
    ),
]
