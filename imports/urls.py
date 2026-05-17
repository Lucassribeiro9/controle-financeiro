"""Rotas do app imports."""

from django.urls import path

from . import views

app_name = "imports"

urlpatterns = [
    path("imports/upload/", views.upload_import, name="upload"),
    path("imports/upload/page/", views.upload_import_page, name="upload-page"),
    path("imports/review/", views.review_imports, name="review"),
    path("imports/review/page/", views.review_imports_page, name="review-page"),
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
