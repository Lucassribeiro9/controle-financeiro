"""Rotas para o app insights."""

from django.urls import path

from . import views

app_name = "insights"

urlpatterns = [
    path("insights/", views.insight_list, name="list"),
    path("insights/recent/", views.recent_insights, name="recent"),
    path(
        "insights/<int:insight_id>/approve/",
        views.approve_insight_view,
        name="approve",
    ),
    path(
        "insights/<int:insight_id>/ignore/",
        views.ignore_insight_view,
        name="ignore",
    ),
    path(
        "insights/<int:insight_id>/silence/",
        views.silence_insight_view,
        name="silence",
    ),
]
