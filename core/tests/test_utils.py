from django.contrib.messages import get_messages
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.forms import Form, fields
from django.test import RequestFactory, TestCase
from core.utils import map_service_errors_to_view


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
        self.assertIn("Erro extra", msgs)

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
