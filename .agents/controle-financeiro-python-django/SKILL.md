---
name: controle-financeiro-python-django
description: Implementacao Python/Django para o app Controle Financeiro. Use ao criar ou alterar models, forms, services, selectors, views, templates, testes, faturas, lancamentos, transferencias, recorrencias, importacoes, metas, dashboards ou qualquer feature do projeto Django financeiro.
---

# Controle Financeiro Python/Django

## Objetivo

Implementar features no projeto Controle Financeiro seguindo a arquitetura local: Django templates, apps por dominio, services para regras de negocio, selectors para consultas, views finas, testes por camada e `Decimal` para dinheiro.

## Workflow

1. Ler a spec ou issue relacionada antes de codar.
2. Identificar apps e arquivos afetados.
3. Colocar regra financeira em `services.py` ou `models.py` quando for invariante simples.
4. Colocar consultas, filtros e agregacoes em `selectors.py`.
5. Manter `views.py` como orquestracao HTTP: request, form, service, messages e redirect.
6. Atualizar templates apenas com apresentacao; evitar regra de negocio no template.
7. Criar ou atualizar testes junto da mudanca.
8. Rodar os comandos de validacao aplicaveis.

## Padrao de App

Use o padrao existente:

```text
models.py       -> dados e invariantes simples
forms.py        -> validacao de formulario
services.py     -> regras de negocio e efeitos
selectors.py    -> consultas, filtros e agregacoes
views.py        -> fluxo HTTP, messages e redirects
urls.py         -> rotas do app
tests/          -> tests de models, services, selectors e views
templates/      -> templates do app
```

## Regras Obrigatorias

- Usar `Decimal`, nunca `float`, para valores financeiros.
- Criar teste para toda classe ou funcao nova.
- Nao tratar transferencia como receita ou despesa.
- Nao marcar recorrencia como paga automaticamente por padrao.
- Compra no credito deve consumir limite mesmo pendente, quando a spec envolver limites.
- Fluxo HTML deve usar `POST -> service -> messages -> redirect`.
- JSON so deve aparecer em endpoint API/async intencional.
- Nao duplicar regra de status entre apps; preferir constantes ou selector compartilhado.
- Nao colocar regra de saldo diretamente em template ou view.

## Padroes de Implementacao

Service financeiro:

```python
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction


@transaction.atomic
def register_payment(*, statement, payment_account, amount: Decimal):
    if amount <= Decimal("0.00"):
        raise ValidationError("O valor deve ser positivo.")

    statement.register_payment(account=payment_account, amount=amount)
    return statement
```

View HTML:

```python
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render


def action_view(request):
    if request.method == "POST":
        try:
            service_action(...)
        except ValidationError as exc:
            messages.error(request, exc.message)
        else:
            messages.success(request, "Acao realizada com sucesso.")
            return redirect("target")

    return render(request, "app/template.html", context)
```

## Testes

Escolher o menor nivel que prova a regra:

- `test_models.py`: invariantes simples e validacoes de model.
- `test_services.py`: regras de negocio, efeitos e impacto financeiro.
- `test_selectors.py`: filtros, agregacoes e ordenacao.
- `test_views.py`: GET, POST, redirects, messages e templates.

Comandos padrao:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Boundaries

Sempre:

- seguir a spec;
- preservar dados financeiros;
- manter mudancas pequenas;
- adicionar testes;
- relatar arquivos alterados.

Perguntar antes:

- adicionar dependencia;
- mudar schema fora da issue;
- alterar CI;
- mudar regra de saldo/fatura retroativamente;
- introduzir API externa;
- mudar single-user para multiusuario.

Nunca:

- commitar segredo ou dado financeiro real;
- remover teste falhando sem justificativa;
- usar `float` para dinheiro;
- retornar JSON cru em fluxo HTML;
- fazer refatoracao ampla junto de feature pequena.
