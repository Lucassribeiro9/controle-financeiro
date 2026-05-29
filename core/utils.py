from django.contrib import messages
from django.core.exceptions import ValidationError
from django.forms import Form
from django.http import HttpRequest


from typing import Optional

def map_service_errors_to_view(
    request: HttpRequest,
    exc: ValidationError,
    form: Optional[Form] = None,
    fallback_message: Optional[str] = None,
):
    """
    Mapeia erros de validação vindos de services para o contexto da view.
    Se um formulário for fornecido, tenta associar erros aos campos.
    Erros que não pertencem a campos (non-field) ou erros sem formulário
    são adicionados ao django.contrib.messages.
    """
    if hasattr(exc, "message_dict") and form:
        for field, errors in exc.message_dict.items():
            if field in form.fields:
                for error in errors:
                    form.add_error(field, error)
            else:
                # Se o campo não existe no form, vai para non_field_errors e messages
                for error in errors:
                    form.add_error(None, error)
                    messages.error(request, error)
    else:
        # Erro simples (string) ou sem formulário associado
        error_msg = fallback_message or str(exc.message if hasattr(exc, "message") else exc)
        if form:
            form.add_error(None, error_msg)
        messages.error(request, error_msg)
