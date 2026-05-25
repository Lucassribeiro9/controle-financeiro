"""Views do app categories."""

from django.contrib import messages
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CategoryForm
from .models import Category


def category_list_page(request: HttpRequest) -> HttpResponse:
    """Renderiza a lista de categorias e subcategorias."""

    categories = (
        Category.objects.select_related("parent")
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
