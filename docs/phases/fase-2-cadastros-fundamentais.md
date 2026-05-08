# Fase 2 - Cadastros Fundamentais

## Objetivo da fase

Criar as entidades base do sistema financeiro pessoal, preparando o projeto para registrar instituicoes, contas, cartoes e categorias.

Referencias:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## O que foi criado

### 1. App `institutions`

Arquivos principais:

- `institutions/apps.py`
- `institutions/models.py`
- `institutions/admin.py`
- `institutions/tests/test_models.py`
- `institutions/migrations/0001_initial.py`

Papel do app:

- Registrar instituicoes financeiras, bancos, carteiras, corretoras ou emissores.
- Servir como base de relacionamento para contas financeiras e cartoes.

Model principal:

- `Institution`

Campos principais:

- `name`
- `official_name`
- `code`
- `is_active`
- `created_at`
- `updated_at`

Regras iniciais:

- Nome unico por instituicao.
- Codigo opcional, mas unico quando informado.
- Ordenacao padrao por nome.

### 2. App `categories`

Arquivos principais:

- `categories/apps.py`
- `categories/models.py`
- `categories/admin.py`
- `categories/tests/test_models.py`
- `categories/migrations/0001_initial.py`

Papel do app:

- Registrar categorias usadas para organizar receitas, despesas, metas e relatorios.
- Permitir uma hierarquia simples entre categoria pai e categoria filha.

Model principal:

- `Category`

Campos principais:

- `name`
- `parent`
- `is_active`
- `created_at`
- `updated_at`

Regras iniciais:

- Nome unico por categoria.
- Categoria filha pode apontar para uma categoria pai.
- Exclusao protegida quando houver categorias vinculadas como filhas.

### 3. App `accounts`

Arquivos principais:

- `accounts/apps.py`
- `accounts/models.py`
- `accounts/admin.py`
- `accounts/tests/test_models.py`
- `accounts/migrations/0001_initial.py`

Papel do app:

- Registrar lugares onde existe saldo financeiro, como conta corrente, poupanca, porquinho, conta global, dinheiro fisico, beneficio e investimento.
- Manter a base para calculo futuro de patrimonio, saldos e transferencias internas.

Model principal:

- `FinancialAccount`

Campos principais:

- `name`
- `institution`
- `account_type`
- `currency`
- `balance`
- `is_active`
- `created_at`
- `updated_at`

Tipos iniciais:

- `checking`
- `savings`
- `piggy_bank`
- `benefit`
- `global`
- `cash`
- `investment`

Moedas iniciais:

- `BRL`
- `USD`

Regras iniciais:

- Toda conta pertence a uma instituicao.
- Saldo usa `Decimal`, evitando `float` para dinheiro.
- Nome da conta deve ser unico dentro da mesma instituicao.
- Mesmo nome pode existir em instituicoes diferentes.

### 4. App `cards`

Arquivos principais:

- `cards/apps.py`
- `cards/models.py`
- `cards/admin.py`
- `cards/tests/test_models.py`
- `cards/migrations/0001_initial.py`

Papel do app:

- Registrar cartoes de credito, beneficio, transporte e pre-pago.
- Preparar a base para faturas, pagamentos e consumo por tipo de cartao nas proximas fases.

Model principal:

- `Card`

Campos principais:

- `name`
- `institution`
- `card_type`
- `credit_limit`
- `statement_closing_day`
- `statement_due_day`
- `payment_account`
- `estimated_balance`
- `is_active`
- `created_at`
- `updated_at`

Tipos iniciais:

- `credit`
- `benefit`
- `transport`
- `prepaid`

Regras iniciais:

- Cartao de credito exige limite, dia de fechamento, dia de vencimento e conta padrao de pagamento.
- Cartao de beneficio exige saldo estimado.
- Dias de fechamento e vencimento devem ficar entre 1 e 31.
- Limite e saldo estimado nao podem ser negativos.
- Nome do cartao deve ser unico dentro da mesma instituicao.

## Admin Django

Todos os cadastros fundamentais foram registrados no Django Admin.

Recursos configurados:

- Campos principais em `list_display`.
- Busca por nome e campos relacionados.
- Filtros por status, tipo, moeda ou instituicao quando aplicavel.
- Ordenacao padrao para facilitar navegacao.

## Testes implementados na fase

### `Institution`

Arquivo:

- `institutions/tests/test_models.py`

Cobertura:

- Criacao com campos obrigatorios.
- Retorno amigavel em `__str__`.
- Restricao de nome unico.

### `Category`

Arquivo:

- `categories/tests/test_models.py`

Cobertura:

- Criacao com campos obrigatorios.
- Retorno amigavel em `__str__`.
- Restricao de nome unico.
- Criacao de categoria pai e categoria filha.

### `FinancialAccount`

Arquivo:

- `accounts/tests/test_models.py`

Cobertura:

- Criacao de conta com saldo em `Decimal`.
- Moeda `BRL` como padrao.
- Exigencia de instituicao.
- Retorno amigavel com conta e instituicao.
- Permissao do mesmo nome em instituicoes diferentes.
- Bloqueio de nome duplicado dentro da mesma instituicao.

### `Card`

Arquivo:

- `cards/tests/test_models.py`

Cobertura:

- Criacao de cartao de credito com configuracoes obrigatorias.
- Validacao de cartao de credito incompleto.
- Criacao de cartao de beneficio com saldo estimado.
- Validacao de cartao de beneficio sem saldo estimado.
- Bloqueio de nome duplicado dentro da mesma instituicao.

Execucao local:

```bash
python3 manage.py test
```

Ou pelo ambiente Docker:

```bash
docker compose run --rm web python manage.py test
```

## Status da fase

Fase 2 concluida conforme os cadastros fundamentais previstos no plano.

Com esta base pronta, a proxima fase pode iniciar o nucleo de movimentacoes financeiras com `Transaction` e `Transfer`.
