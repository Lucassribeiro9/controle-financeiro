"""Autenticacao server-side: middleware de login obrigatorio e marcador de rotas JSON."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.middleware import LoginRequiredMiddleware
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.http import Http404, JsonResponse

SINGLE_USER_ERROR = (
    "O sistema e single-user: ja existe um usuario ativo. "
    "Desative ou remova o usuario existente antes de ativar outro."
)


def api_login_required(view_func):
    """Marca uma view JSON para responder 401 (em vez de redirecionar) a anonimos.

    Deve ser o decorator mais externo da view, pois o middleware le o atributo
    diretamente da funcao resolvida pela URL.
    """

    view_func.api_login_required = True
    return view_func


class SingleUserBackend(ModelBackend):
    """Autentica somente quando existe exatamente um usuario ativo (fail-closed).

    Se, por qualquer caminho (SQL direto, bulk_create), existir mais de um
    usuario ativo, ninguem autentica, nem no login nem no admin.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if get_user_model().objects.filter(is_active=True).count() != 1:
            return None
        return super().authenticate(request, username, password, **kwargs)


def enforce_single_active_user(sender, instance, **kwargs):
    """Impede salvar um segundo usuario ativo (signal pre_save de User)."""

    if not instance.is_active:
        return
    others = sender.objects.filter(is_active=True)
    if instance.pk is not None:
        others = others.exclude(pk=instance.pk)
    if others.exists():
        raise ValidationError(SINGLE_USER_ERROR)


def connect_single_user_guard():
    """Registra o guard single-user no model de usuario configurado."""

    pre_save.connect(
        enforce_single_active_user,
        sender=get_user_model(),
        dispatch_uid="core.single_user_guard",
    )


class ApiAwareLoginRequiredMiddleware(LoginRequiredMiddleware):
    """Exige login em todas as rotas; views JSON marcadas recebem 401/404 JSON."""

    def process_exception(self, request, exception):
        match = request.resolver_match
        if (
            isinstance(exception, Http404)
            and match is not None
            and getattr(match.func, "api_login_required", False)
        ):
            return JsonResponse({"error": "Recurso nao encontrado."}, status=404)
        return None

    def handle_no_permission(self, request, view_func):
        if getattr(view_func, "api_login_required", False):
            return JsonResponse(
                {"error": "Autenticação obrigatória."},
                status=401,
            )
        return super().handle_no_permission(request, view_func)
