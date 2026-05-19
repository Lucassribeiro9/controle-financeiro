"""Rotas para o app goals."""

from django.urls import path

from . import views

app_name = "goals"

urlpatterns = [
    path("goals/", views.goal_list_page, name="list"),
    path("goals/monthly/", views.monthly_goals_page, name="monthly-goals"),
    path("goals/<int:goal_id>/", views.goal_detail_page, name="detail"),
]
