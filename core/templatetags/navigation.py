"""Estado da navegação principal: seção ativa a partir de namespace e path (spec 017, 3.2)."""

from django import template

register = template.Library()

TRANSFERS_PREFIX = "/transactions/transfers/"
STATEMENTS_PREFIX = "/cards/statements/"
ADMIN_PREFIX = "/admin/"

# Seções que vivem na folha "Mais" (as demais estão na barra inferior).
MORE_SECTIONS = frozenset(
    {
        "reports",
        "goals",
        "accounts",
        "cards",
        "transfers",
        "installments",
        "recurrences",
        "imports",
        "categories",
        "institutions",
        "insights",
        "admin",
    }
)

NAMESPACE_SECTIONS = {
    "core": "home",
    "reports": "reports",
    "goals": "goals",
    "accounts": "accounts",
    "installments": "installments",
    "recurrences": "recurrences",
    "imports": "imports",
    "categories": "categories",
    "institutions": "institutions",
    "insights": "insights",
}


def section_for(namespace, path):
    """Devolve a seção ativa; vazio quando a tela não pertence à navegação."""

    if path.startswith(ADMIN_PREFIX):
        return "admin"
    if namespace == "transactions":
        return "transfers" if path.startswith(TRANSFERS_PREFIX) else "transactions"
    if namespace == "cards":
        return "statements" if path.startswith(STATEMENTS_PREFIX) else "cards"
    return NAMESPACE_SECTIONS.get(namespace or "", "")


@register.simple_tag(takes_context=True)
def nav_state(context):
    """Seção ativa e se ela está na folha "Mais". Não consulta o banco."""

    request = context.get("request")
    if request is None:
        return {"section": "", "in_more": False}

    match = getattr(request, "resolver_match", None)
    namespace = match.namespace if match else None
    section = section_for(namespace, request.path)
    return {"section": section, "in_more": section in MORE_SECTIONS}
