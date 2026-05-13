from django.contrib import admin
from .models import Goal, MonthlyGoal
# Register your models here.

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    """Admin para o model Goal."""
    list_display = ("name", "goal_type", "target_amount", "start_date", "target_date", "is_active")
    list_filter = ("goal_type", "is_active")
    search_fields = ("name",)

@admin.register(MonthlyGoal)
class MonthlyGoalAdmin(admin.ModelAdmin):
    """Admin para o model MonthlyGoal."""
    list_display = ("goal", "year", "month", "target_amount", "current_amount", "status")
    list_filter = ("year", "month", "status")
    search_fields = ("goal__name",)