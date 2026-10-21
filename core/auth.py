"""Autenticacao server-side: middleware de login obrigatorio e marcador de rotas JSON."""

from django.contrib.auth.middleware import LoginRequiredMiddleware
from django.http import JsonResponse


def api_login_required(view_func):
    """Marca uma view JSON para responder 401 (em vez de redirecionar) a anonimos.

    Deve ser o decorator mais externo da view, pois o middleware le o atributo
    diretamente da funcao resolvida pela URL.
    """

    view_func.api_login_required = True
    return view_func


class ApiAwareLoginRequiredMiddleware(LoginRequiredMiddleware):
    """Exige login em todas as rotas; views JSON marcadas recebem 401 JSON."""

    def handle_no_permission(self, request, view_func):
        if getattr(view_func, "api_login_required", False):
            return JsonResponse(
                {"error": "Autenticação obrigatória."},
                status=401,
            )
        return super().handle_no_permission(request, view_func)
