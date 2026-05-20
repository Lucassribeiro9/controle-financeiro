"""Rotas para o app installments."""

from django.urls import path

from . import views

app_name = "installments"

urlpatterns = [
    path("installments/", views.installment_list_page, name="list"),
    path("installments/create/", views.installment_create_page, name="create"),
    path("installments/<int:plan_id>/", views.installment_detail_page, name="detail"),
    path(
        "installments/<int:plan_id>/cancel/",
        views.installment_cancel_page,
        name="cancel",
    ),
]
