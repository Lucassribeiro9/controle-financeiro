"""Rotas do app imports."""

from django.urls import path

from . import views

app_name = "imports"

urlpatterns = [
    path("imports/upload/", views.upload_import, name="upload"),
    path("imports/review/", views.review_imports, name="review"),
    path(
        "imports/<int:imported_transaction_id>/confirm/",
        views.confirm_import,
        name="confirm",
    ),
    path(
        "imports/<int:imported_transaction_id>/discard/",
        views.discard_import,
        name="discard",
    ),
]
