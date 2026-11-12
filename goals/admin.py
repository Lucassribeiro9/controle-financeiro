from django import forms
from django.contrib import admin

from .models import Goal, MonthlyGoal
from .services import validate_goal_accounts_currency


class GoalAdminForm(forms.ModelForm):
    """Valida moeda unica nas contas de objetivos de acumulo (ADR-016)."""

    class Meta:
        model = Goal
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        accounts = cleaned_data.get("accounts")
        if accounts is not None and cleaned_data.get("goal_type") == (
            Goal.GoalType.ACCUMULATION
        ):
            try:
                validate_goal_accounts_currency(accounts)
            except forms.ValidationError as exc:
                self.add_error("accounts", exc.messages)
        return cleaned_data


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    """Admin para o model Goal."""
    form = GoalAdminForm
    list_display = ("name", "goal_type", "target_amount", "start_date", "target_date", "is_active")
    list_filter = ("goal_type", "is_active")
    search_fields = ("name",)

@admin.register(MonthlyGoal)
class MonthlyGoalAdmin(admin.ModelAdmin):
    """Admin para o model MonthlyGoal."""
    list_display = ("goal", "year", "month", "target_amount", "current_amount", "status")
    list_filter = ("year", "month", "status")
    search_fields = ("goal__name",)
