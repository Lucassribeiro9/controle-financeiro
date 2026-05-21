"""Rotas para o app categories."""

from django.urls import path

from . import views

app_name = "categories"

urlpatterns = [
    path("categories/", views.category_list_page, name="list"),
    path("categories/create/", views.category_create_page, name="create"),
    path(
        "categories/<int:category_id>/edit/",
        views.category_update_page,
        name="update",
    ),
]
