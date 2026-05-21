"""Rotas para o app accounts."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("accounts/", views.account_list_page, name="list"),
    path("accounts/create/", views.account_create_page, name="create"),
    path("accounts/<int:account_id>/", views.account_detail_page, name="detail"),
    path("accounts/<int:account_id>/edit/", views.account_update_page, name="update"),
]
