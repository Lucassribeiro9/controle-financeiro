"""Rotas para o app institutions."""

from django.urls import path

from . import views

app_name = "institutions"

urlpatterns = [
    path("institutions/", views.institution_list_page, name="list"),
    path("institutions/create/", views.institution_create_page, name="create"),
    path(
        "institutions/<int:institution_id>/edit/",
        views.institution_update_page,
        name="update",
    ),
]
