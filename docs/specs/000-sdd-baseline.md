# Spec 000 - Baseline SDD

## Objetivo

Definir o contrato comum para todas as specs do projeto Controle Financeiro.

Cada spec numerada deve focar no problema de produto ou tecnico que resolve, mas herda desta baseline os comandos, estrutura, estilo, estrategia de testes e limites de atuacao.

Esta baseline e obrigatoria para as proximas issues do projeto.

## Tech Stack

- Python 3.12.
- Django 6.0.5.
- SQLite no MVP.
- Django templates.
- CSS em `static/css/app.css`.
- Chart.js em telas de dashboard/relatorio quando o grafico ajudar a decisao.
- Testes seguindo a estrutura atual do projeto.
- Docker/Docker Compose para execucao local padronizada.
- GitHub Actions para CI.

## Commands

Comandos obrigatorios para validar uma issue antes do PR:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Pre-requisito local:

- ativar o ambiente virtual do projeto antes de rodar os comandos, garantindo que `python` aponte para o interpretador do `venv`;
- quando o ambiente virtual nao estiver ativado, usar `venv/bin/python` de forma explicita.

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

## Migration Policy

Mudancas de schema e migrations so sao permitidas quando a issue declarar explicitamente esse escopo.

Issue com schema deve registrar:

- quais models/campos/constraints entram na mudanca;
- quais migrations sao esperadas;
- qual impacto existe em dados financeiros ja gravados;
- quais testes provam a alteracao;
- qual comando valida que nao ha migrations inesperadas.

Criterios de aceite para issue com migration devem citar os arquivos de migration esperados, por exemplo:

```text
Acceptance: migration `transactions/migrations/0008_add_paid_at.py` existe e aplica o campo `paid_at` sem alterar saldos existentes.
Verify: `python manage.py makemigrations --check --dry-run` nao gera migrations adicionais depois da migration versionada.
```

PR sem mudanca de schema deve passar em:

```bash
python manage.py makemigrations --check --dry-run
```

Se esse comando indicar migration pendente em uma issue que nao declarou schema, a mudanca deve voltar para a fase de spec/issue antes de continuar.

## Project Structure

Estrutura relevante da fase atual:

```text
project/        -> settings, urls, ASGI/WSGI
core/           -> home, navegacao e utilitarios globais
institutions/   -> instituicoes financeiras, bancos e emissores
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

Apps Django instalados nesta fase:

```text
core
institutions
accounts
categories
cards
installments
transactions
recurrences
goals
reports
imports
insights
rates
```

Diretorios compartilhados relevantes:

```text
project/
templates/
static/
docs/plans/
docs/specs/
```

Nao ha apps planejados listados como se ja existissem nesta baseline. Quando um app novo entrar no roadmap, ele deve ser identificado como planejado ate ser criado e registrado em `INSTALLED_APPS`.

Esta lista de apps e diretorios e a referencia canonica da fase atual do projeto.

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
- a estrutura de testes atual do projeto deve ser preservada;
- criterios de aceite testaveis sao obrigatorios antes de abrir issue para implementacao.

Politica minima por tipo de mudanca:

- model: testar invariantes simples, validacoes, defaults, constraints esperadas e metodos que alterem estado financeiro;
- service: testar regra de negocio, efeitos colaterais, transacoes atomicas, validacoes de erro e impacto em saldo, fatura, limite ou status;
- selector: testar filtros, ordenacao, agregacoes, inclusao/exclusao por status e cenarios com banco vazio;
- view GET: testar status code, template usado, contexto essencial e links/acoes esperados quando forem parte do aceite;
- view POST: testar sucesso, erro de validacao, chamada do service quando aplicavel, `messages` e redirect;
- template/helper: testar logica condicional relevante, formatacao de valores, status, badges ou estados vazios quando isso puder quebrar regra de exibicao;
- mudanca visual relevante: validar manualmente desktop e mobile, incluindo estados vazio, com dados, erro e filtros sem resultado quando aplicavel.

Regras operacionais:

- regra financeira nova ou alterada exige teste de service ou model;
- consulta nova ou alterada exige teste de selector;
- fluxo HTML com POST exige teste de view cobrindo `messages` e redirect;
- funcao ou classe nova exige teste no menor nivel que prove seu comportamento;
- mudanca puramente documental nao exige teste automatizado, mas deve passar por revisao manual e pelos comandos obrigatorios antes do PR.

## Boundaries

### Always

- Rodar os comandos de validacao antes do PR.
- Criar ou atualizar testes junto da mudanca.
- Atualizar spec quando a decisao de produto mudar.
- Preservar dados financeiros e regras de saldo.
- Usar branch curta seguindo o padrao documentado.

### Ask First

- Alterar schema de banco fora do escopo explicito da issue.
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

Antes de quebrar em issue de implementacao:

- [ ] A spec tem objetivo claro.
- [ ] A spec declara fora de escopo.
- [ ] A spec referencia esta baseline.
- [ ] A spec tem criterios de aceite testaveis.
- [ ] A spec tem open questions ou declara que nao ha questoes abertas.
- [ ] A spec declara explicitamente se muda schema ou se nao muda schema.
- [ ] A spec foi quebrada em issues pequenas.
- [ ] A ordem das tasks respeita dependencias.

## Issue SDD Checklist

Toda issue de implementacao deve ser pequena, revisavel e ligada a uma spec. Antes de abrir a issue, conferir:

- [ ] Titulo segue Conventional Commits em portugues.
- [ ] Contexto explica o problema e referencia a spec relacionada.
- [ ] Objetivo descreve o resultado esperado da issue.
- [ ] Escopo lista somente o que entra nesta entrega.
- [ ] Fora de escopo lista o que nao deve ser implementado agora.
- [ ] Criterios de aceite sao objetivos e testaveis.
- [ ] Testes esperados indicam comandos, testes automatizados ou validacao manual.
- [ ] Arquivos provaveis indicam onde a mudanca deve acontecer.
- [ ] A issue declara se muda schema ou se nao muda schema.
- [ ] A issue e pequena o bastante para um PR claro.

Campos obrigatorios da issue:

```markdown
## Contexto

## Objetivo

## Escopo

## Fora de Escopo

## Criterios de Aceite

## Testes Esperados

## Arquivos Provaveis
```

Regras operacionais:

- uma issue deve nascer de uma spec aprovada ou atualizar a spec antes da implementacao;
- cada criterio de aceite deve ter uma forma de verificacao;
- arquivos provaveis ajudam a limitar o escopo, mas nao autorizam mudancas fora da issue;
- se a issue envolver schema, a politica de migrations desta baseline deve ser seguida;
- mudancas de produto nao devem entrar em issue puramente documental.

## Decisoes da Spec Review

- Esta baseline passa a ser contrato obrigatorio para as proximas issues.
- O trio de validacao (`check`, `makemigrations --check --dry-run` e `test`) e obrigatorio antes de PR.
- A estrutura de testes atual do projeto deve ser mantida.
- A lista de apps e diretorios desta baseline e a referencia canonica da fase atual.
- Mudancas de schema e migrations so entram quando a issue permitir explicitamente.
- Criterios de aceite testaveis sao obrigatorios antes de abrir issue de implementacao.
- Toda spec numerada deve declarar fora de escopo, criterios de aceite, open questions e task breakdown.

## Issues Sugeridas

- Validar comandos obrigatorios no ambiente atual.
- Alinhar a lista de apps desta baseline quando a estrutura real do projeto mudar.
- Documentar politica minima de testes por tipo de mudanca.
- Documentar politica de migrations quando houver a primeira issue com schema.
- Criar checklist operacional para abrir issues pequenas a partir das specs.

## Validacao dos Comandos Obrigatorios

Validacao executada em 2026-05-27.

Resultado com os comandos literais:

```text
python manage.py check
Resultado: falhou porque o binario `python` nao existe no shell atual.

python manage.py makemigrations --check --dry-run
Resultado: falhou pelo mesmo motivo.

python manage.py test
Resultado: falhou pelo mesmo motivo.
```

Resultado usando o ambiente virtual local:

```text
venv/bin/python manage.py check
Resultado: passou. System check identified no issues.

venv/bin/python manage.py makemigrations --check --dry-run
Resultado: passou. No changes detected.

venv/bin/python manage.py test
Resultado: passou. 319 tests executados com OK.
```

Bloqueio acionavel:

- antes de executar os comandos obrigatorios como `python manage.py ...`, ativar o `venv` do projeto ou criar um alias local em que `python` aponte para Python 3.12 com as dependencias instaladas.
