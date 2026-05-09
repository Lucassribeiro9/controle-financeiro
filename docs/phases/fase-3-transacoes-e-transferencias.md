# Fase 3 - Transacoes e Transferencias

## Objetivo da fase

Criar o nucleo de movimentacoes financeiras para registrar receitas, despesas, compras no cartao, previsoes, pagamentos de fatura e transferencias internas entre contas.

Referencias:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## O que foi criado

### 1. App `transactions`

Arquivos principais:

- `transactions/apps.py`
- `transactions/models.py`
- `transactions/services.py`
- `transactions/admin.py`
- `transactions/tests/test_models.py`
- `transactions/tests/test_services.py`
- `transactions/migrations/0001_initial.py`

Papel do app:

- Centralizar o registro de movimentacoes financeiras do sistema.
- Separar o conceito de transacao (receita/despesa/compra/previsao) do conceito de transferencia interna entre contas.

### 2. Model `Transaction`

Campos principais:

- `description`
- `amount`
- `transaction_type`
- `status`
- `account`
- `category`
- `card`
- `date`
- `notes`
- `created_at`
- `updated_at`

Tipos iniciais:

- `income`
- `expense`
- `adjustment`
- `card_purchase`
- `forecast`
- `statement_payment`

Status iniciais:

- `forecasted`
- `pending`
- `paid`
- `partially_paid`
- `late`
- `canceled`
- `ignored`

Regras iniciais:

- Valor deve ser maior que zero.
- `card_purchase` exige cartao vinculado.
- Tipos diferentes de `card_purchase` exigem conta financeira vinculada.
- Ordenacao padrao por data mais recente.

### 3. Model `Transfer`

Campos principais:

- `description`
- `amount`
- `from_account`
- `destination_account`
- `date`
- `notes`
- `created_at`
- `updated_at`

Regras iniciais:

- Valor deve ser maior que zero.
- Conta de origem deve ser diferente da conta de destino.
- Transferencia interna e registrada separadamente de receita/despesa.

### 4. Servicos

Arquivo:

- `transactions/services.py`

Servicos implementados:

- `create_transaction`
- `create_transfer`

Comportamento atual:

- `create_transaction` valida e persiste a transacao com `full_clean` e transacao atomica.
- Receita (`income`) aumenta saldo da conta vinculada.
- Despesa (`expense`) e pagamento de fatura (`statement_payment`) reduzem saldo da conta vinculada.
- Previsao (`forecast`) e compra no cartao (`card_purchase`) nao alteram saldo da conta no momento do lancamento.
- `create_transfer` valida e move saldo da origem para o destino com bloqueio transacional (`select_for_update`).

## Admin Django

Models registrados:

- `Transaction`
- `Transfer`

Recursos configurados:

- `list_display` com campos principais.
- `search_fields` para descricao e relacionamentos.
- `list_filter` por tipo, status, data e contas relacionadas.
- Ordenacao por data mais recente.

## Testes implementados na fase

### `Transaction` (model)

Arquivo:

- `transactions/tests/test_models.py`

Cobertura:

- Criacao de receita vinculada a conta.
- Criacao de despesa com categoria.
- Exigencia de cartao para `card_purchase`.
- Validacao de valor positivo.
- Validacao de `__str__`.

### `Transfer` (model)

Arquivo:

- `transactions/tests/test_models.py`

Cobertura:

- Criacao entre contas diferentes.
- Validacao de valor positivo.
- Bloqueio de transferencia para a mesma conta.
- Garantia de que transferencia nao cria `Transaction` automaticamente.
- Validacao de `__str__`.

### Servicos (`create_transaction` e `create_transfer`)

Arquivo:

- `transactions/tests/test_services.py`

Cobertura:

- Receita aumenta saldo da conta.
- Despesa reduz saldo da conta.
- Pagamento de fatura reduz saldo da conta.
- Previsao nao altera saldo.
- Compra no cartao nao altera saldo da conta de pagamento.
- Transferencia move saldo da conta de origem para a conta de destino.

Execucao local:

```bash
python3 manage.py test transactions
```

Ou pelo ambiente Docker:

```bash
docker compose run --rm web python manage.py test transactions
```

## Status da fase

Fase 3 concluida conforme o nucleo inicial de transacoes e transferencias previsto no plano.

Com esta base pronta, a proxima fase pode evoluir o fluxo de cartoes e faturas.
