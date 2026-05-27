# Spec 000 - Baseline SDD

## Objetivo

Definir o contrato comum para todas as specs do projeto Controle Financeiro.

Cada spec numerada deve focar no problema de produto ou tecnico que resolve, mas herda desta baseline os comandos, estrutura, estilo, estrategia de testes e limites de atuacao.

## Tech Stack

- Python 3.12.
- Django 6.0.5.
- SQLite no MVP.
- Django templates.
- CSS em `static/css/app.css`.
- Chart.js em telas de dashboard/relatorio quando o grafico ajudar a decisao.
- Testes com Django TestCase e/ou pytest-django, conforme padrao ja existente no app.
- Docker/Docker Compose para execucao local padronizada.
- GitHub Actions para CI.

## Commands

Comandos padrao para validar uma issue antes do PR:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Comandos auxiliares:

```bash
python manage.py runserver
docker compose up --build
docker compose run --rm web python manage.py test
```

Quando tooling futuro for adotado:

```bash
ruff check .
coverage run manage.py test
coverage report
pre-commit run --all-files
```

## Project Structure

Estrutura relevante:

```text
project/        -> settings, urls, ASGI/WSGI
core/           -> home, navegacao e utilitarios globais
accounts/       -> contas, caixinhas e saldos
cards/          -> cartoes, faturas e pagamentos
categories/     -> categorias de transacoes
transactions/   -> lancamentos e transferencias
installments/   -> parcelamentos
recurrences/    -> recorrencias e previsoes
goals/          -> objetivos e metas mensais
reports/        -> dashboards e relatorios
imports/        -> importacao e revisao de arquivos
insights/       -> sugestoes automaticas
rates/          -> taxas, rendimentos e simulacoes
templates/      -> base e partials compartilhados
static/         -> CSS e assets estaticos
docs/plans/     -> planos e roadmap
docs/specs/     -> specs SDD
```

Padrao por app:

```text
models.py       -> dados e invariantes simples
forms.py        -> validacao de formulario
services.py     -> regras de negocio e efeitos
selectors.py    -> consultas e agregacoes
views.py        -> orquestracao HTTP, messages e redirects
urls.py         -> rotas do app
tests/          -> testes de models, services, selectors e views
templates/      -> templates especificos do app
```

## Code Style

Regras principais:

- usar `Decimal` para valores financeiros;
- manter regra de negocio em services/selectors, nao em views/templates;
- preferir nomes explicitos;
- evitar duplicacao de regra financeira;
- criar teste para toda classe ou funcao nova;
- usar messages/redirect em fluxos HTML;
- manter JSON apenas para endpoint API/async intencional.

Exemplo esperado:

```python
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction


@transaction.atomic
def pay_statement(*, statement, payment_account, amount: Decimal):
    if amount <= Decimal("0.00"):
        raise ValidationError("O valor do pagamento deve ser positivo.")

    statement.register_payment(account=payment_account, amount=amount)
    return statement
```

## Testing Strategy

Toda spec deve indicar testes esperados em pelo menos um destes niveis:

- model: invariantes e validacoes simples;
- service: regra de negocio, impacto financeiro e efeitos;
- selector: consultas, filtros e agregacoes;
- view: GET, POST, redirects, messages e templates;
- template/helper: formatacao ou componentes condicionais relevantes.

Padrao minimo por issue:

- uma mudanca de regra pede teste de service ou model;
- uma mudanca de consulta pede teste de selector;
- uma mudanca de fluxo web pede teste de view;
- uma mudanca visual relevante pede validacao manual desktop/mobile, alem de smoke test quando possivel.

## Boundaries

### Always

- Rodar os comandos de validacao antes do PR.
- Criar ou atualizar testes junto da mudanca.
- Atualizar spec quando a decisao de produto mudar.
- Preservar dados financeiros e regras de saldo.
- Usar branch curta seguindo o padrao documentado.

### Ask First

- Alterar schema de banco fora do escopo da issue.
- Adicionar dependencia nova.
- Mudar CI/CD.
- Alterar fluxo de saldo ou fatura de forma retroativa.
- Introduzir API externa.
- Mudar decisao de single-user para multiusuario.

### Never

- Commitar segredos ou dados financeiros reais.
- Remover teste falhando sem corrigir ou justificar.
- Fazer lancamento recorrente virar pago automaticamente por padrao.
- Tratar transferencia como receita ou despesa.
- Retornar JSON cru em fluxo HTML sem intencao explicita.

## Spec Readiness Checklist

Antes de implementar:

- [ ] A spec tem objetivo claro.
- [ ] A spec declara fora de escopo.
- [ ] A spec referencia esta baseline.
- [ ] A spec tem criterios de aceite testaveis.
- [ ] A spec tem open questions ou declara que nao ha questoes abertas.
- [ ] A spec foi quebrada em issues pequenas.
- [ ] A ordem das tasks respeita dependencias.
