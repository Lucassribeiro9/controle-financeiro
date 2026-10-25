from django.contrib.messages import get_messages
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.forms import Form, fields
from django.test import RequestFactory, TestCase
from core.errors import (
    map_service_errors_to_view,
    validation_error_messages,
    validation_error_response,
    validation_error_text,
)


class TestForm(Form):
    amount = fields.DecimalField()
    description = fields.CharField()


from django.http import HttpResponse

class MapServiceErrorsToViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request_with_messages(self, path="/"):
        request = self.factory.post(path)
        
        # Adiciona suporte a sessao e mensagens manualmente ao request do factory
        def get_response(r): return HttpResponse()
        
        middleware = SessionMiddleware(get_response)
        middleware.process_request(request)
        request.session.save()
        
        messages = MessageMiddleware(get_response)
        messages.process_request(request)
        return request

    def test_map_field_errors_to_form(self):
        request = self._get_request_with_messages()
        form = TestForm(data={"amount": "100", "description": "test"})
        form.is_valid()  # Limpa erros iniciais
        
        exc = ValidationError({"amount": ["Valor inválido"], "non_existent": ["Erro extra"]})
        
        map_service_errors_to_view(request, exc, form=form)
        
        self.assertIn("amount", form.errors)
        self.assertEqual(list(form.errors["amount"]), ["Valor inválido"])
        
        # Erro de campo inexistente deve ir para non_field_errors e messages
        self.assertIn("__all__", form.errors)
        self.assertEqual(form.errors["__all__"], ["Erro extra"])
        storage = get_messages(request)
        msgs = [str(m) for m in storage]
        self.assertNotIn("Erro extra", msgs)

    def test_map_simple_error_to_messages_without_form(self):
        request = self._get_request_with_messages()
        exc = ValidationError("Saldo insuficiente")
        
        map_service_errors_to_view(request, exc)
        
        storage = get_messages(request)
        msgs = [str(m) for m in storage]
        self.assertIn("Saldo insuficiente", msgs)

    def test_use_fallback_message(self):
        request = self._get_request_with_messages()
        exc = ValidationError("Erro técnico obscuro")
        
        map_service_errors_to_view(request, exc, fallback_message="Houve um problema operacional")
        
        storage = get_messages(request)
        msgs = [str(m) for m in storage]
        self.assertIn("Houve um problema operacional", msgs)

    def test_dict_error_without_form_is_readable(self):
        request = self._get_request_with_messages()
        exc = ValidationError({"amount": ["Valor invalido"], "__all__": ["Erro geral"]})

        map_service_errors_to_view(request, exc)

        msgs = [str(m) for m in get_messages(request)]
        self.assertEqual(len(msgs), 1)
        self.assertIn("Valor invalido", msgs[0])
        self.assertIn("Erro geral", msgs[0])
        self.assertNotIn("{", msgs[0])
        self.assertNotIn("[", msgs[0])

    def test_list_error_with_form_becomes_one_general_error_per_message(self):
        request = self._get_request_with_messages()
        form = TestForm(data={"amount": "100", "description": "test"})
        form.is_valid()

        exc = ValidationError(["Primeiro erro", "Segundo erro"])
        map_service_errors_to_view(request, exc, form=form)

        self.assertEqual(list(form.errors["__all__"]), ["Primeiro erro", "Segundo erro"])

    def test_fallback_message_has_priority_with_form(self):
        request = self._get_request_with_messages()
        form = TestForm(data={"amount": "100", "description": "test"})
        form.is_valid()

        map_service_errors_to_view(
            request, ValidationError("Tecnico"), form=form, fallback_message="Amigavel"
        )

        self.assertEqual(list(form.errors["__all__"]), ["Amigavel"])


class ValidationErrorHelpersTests(TestCase):
    def test_messages_from_dict_include_all_fields(self):
        exc = ValidationError({"a": ["Erro A"], "__all__": ["Erro geral"]})
        self.assertEqual(validation_error_messages(exc), ["Erro A", "Erro geral"])

    def test_messages_from_list(self):
        exc = ValidationError(["Um", "Dois"])
        self.assertEqual(validation_error_messages(exc), ["Um", "Dois"])

    def test_messages_interpolate_params(self):
        exc = ValidationError("Valor maximo %(max)s", params={"max": 10})
        self.assertEqual(validation_error_messages(exc), ["Valor maximo 10"])

    def test_simple_error(self):
        self.assertEqual(validation_error_text(ValidationError("Simples")), "Simples")

    def test_text_joins_with_space(self):
        exc = ValidationError({"a": ["Erro A"], "b": ["Erro B"]})
        self.assertEqual(validation_error_text(exc), "Erro A Erro B")

    def test_json_response_400(self):
        response = validation_error_response(ValidationError({"a": ["Erro A"]}))
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {"error": "Erro A"})
