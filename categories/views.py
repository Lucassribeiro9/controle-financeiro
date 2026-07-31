"""Views do app categories."""

import datetime
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from goals.services import create_reduction_goal_for_category

from .forms import CategoryForm
from .models import Category
from .selectors import get_categories_with_monthly_spent


def category_list_page(request: HttpRequest) -> HttpResponse:
    """Renderiza a lista de categorias e subcategorias."""

    categories = (
        get_categories_with_monthly_spent(timezone.localdate())
        .annotate(children_count=Count("children"))
        .order_by("parent__name", "name")
    )

    return render(
        request,
        "categories/list.html",
        {"categories": categories},
    )


def category_create_page(request: HttpRequest) -> HttpResponse:
    """Renderiza e processa o formulario de criacao de categoria."""

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria criada com sucesso.")
            return redirect("categories:list")
    else:
        form = CategoryForm()

    return render(
        request,
        "categories/form.html",
        {
            "form": form,
            "form_title": "Nova categoria",
            "submit_label": "Salvar",
        },
    )


def category_update_page(request: HttpRequest, category_id: int) -> HttpResponse:
    """Renderiza e processa o formulario de edicao de categoria."""

    category = get_object_or_404(
        Category.objects.select_related("parent"),
        pk=category_id,
    )

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria atualizada com sucesso.")
            return redirect("categories:list")
    else:
        form = CategoryForm(instance=category)

    return render(
        request,
        "categories/form.html",
        {
            "form": form,
            "category": category,
            "form_title": "Editar categoria",
            "submit_label": "Salvar alterações",
        },
    )


def category_create_goal_page(request: HttpRequest, category_id: int) -> HttpResponse:
    """Renderiza e processa o formulario de criacao de meta mensal por categoria."""

    category = get_object_or_404(Category, pk=category_id)
    today = datetime.date.today()
    error = None

    if request.method == "POST":
        raw_amount = request.POST.get("target_amount", "").strip()
        year = int(request.POST.get("year", today.year))
        month = int(request.POST.get("month", today.month))

        try:
            target_amount = Decimal(raw_amount)
            create_reduction_goal_for_category(
                category=category,
                year=year,
                month=month,
                target_amount=target_amount,
            )
            messages.success(
                request,
                f"Meta mensal de R$ {target_amount:.2f} criada para '{category.name}'.",
            )
            return redirect("categories:list")
        except (ValidationError, Exception) as exc:
            error = exc

    return render(
        request,
        "categories/create_goal.html",
        {
            "category": category,
            "year": today.year,
            "month": today.month,
            "error": error,
        },
    )
