"""Helpers centrais para apresentar ValidationError (ADR-012, item 5)."""

from typing import Optional

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.forms import Form
from django.http import HttpRequest, JsonResponse


def validation_error_messages(exc: ValidationError) -> list[str]:
    """Lista legivel de mensagens, com params interpolados."""

    if hasattr(exc, "error_dict"):
        result: list[str] = []
        for field_errors in exc.message_dict.values():
            result.extend(str(message) for message in field_errors)
        return result
    return [str(message) for message in exc.messages]


def validation_error_text(exc: ValidationError) -> str:
    """Mensagens de ValidationError unidas por espaco."""

    return " ".join(validation_error_messages(exc))


def validation_error_response(exc: ValidationError, status: int = 400) -> JsonResponse:
    """Resposta JSON {"error": texto} para APIs."""

    return JsonResponse({"error": validation_error_text(exc)}, status=status)


def map_service_errors_to_view(
    request: HttpRequest,
    exc: ValidationError,
    form: Optional[Form] = None,
    fallback_message: Optional[str] = None,
) -> None:
    """
    Mapeia erros de validacao vindos de services para o contexto da view.

    Com form, erros de campo vao para o campo; campos que o form nao tem e
    erros sem campo viram erros gerais. Sem form, uma unica mensagem legivel
    vai para django.contrib.messages. fallback_message tem prioridade.
    """

    if fallback_message:
        if form:
            form.add_error(None, fallback_message)
        else:
            messages.error(request, fallback_message)
        return

    if not form:
        messages.error(request, validation_error_text(exc))
        return

    if hasattr(exc, "error_dict"):
        for field, errors in exc.message_dict.items():
            target = field if field in form.fields else None
            for error in errors:
                form.add_error(target, error)
        return

    for message in exc.messages:
        form.add_error(None, message)
