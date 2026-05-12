# Fase 4 - Cartoes e Faturas

## Objetivo da fase

Implementar o fluxo inicial de faturas de cartao de credito, permitindo vincular compras no cartao a uma fatura mensal, fechar a fatura, pagar total ou parcialmente e manter a regra de que pagamento de fatura nao duplica despesa nos relatorios.

Referencias:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## O que foi criado

### 1. Model `CardStatement`

Arquivo principal:

- `cards/models.py`

Papel do model:

- Representar uma fatura mensal de cartao de credito.
- Guardar mes e ano de referencia.
- Guardar datas de fechamento e vencimento.
- Controlar valor esperado, valor fechado, valor pago e status.
- Permitir uma conta de pagamento diferente da conta padrao do cartao.

Campos principais:

- `card`
- `year`
- `month`
- `expected_amount`
- `closed_amount`
- `paid_amount`
- `closing_date`
- `due_date`
- `status`
- `payment_account`
- `created_at`
- `updated_at`

Status iniciais:

- `forecasted`
- `open`
- `pending`
- `partially_paid`
- `paid`
- `late`
- `canceled`

Regras iniciais:

- Fatura so pode pertencer a cartao de credito.
- Mes deve estar entre 1 e 12.
- Deve existir apenas uma fatura por cartao, mes e ano.
- Valores monetarios nao podem ser negativos.
- Valor pago nao pode superar o valor fechado.
- Quando a fatura nao informa conta de pagamento, ela herda a conta padrao do cartao.

### 2. Vinculo entre `Transaction` e `CardStatement`

Arquivo principal:

- `transactions/models.py`

Foi adicionado o campo:

- `statement`

Papel do vinculo:

- Permitir que compras no cartao (`card_purchase`) sejam associadas a uma fatura.
- Permitir que pagamentos de fatura (`statement_payment`) tambem referenciem a fatura paga.

Regras iniciais:

- Apenas `card_purchase` e `statement_payment` podem ter fatura vinculada.
- A fatura vinculada deve pertencer ao mesmo cartao da transacao.

### 3. Migrations

Arquivos:

- `cards/migrations/0002_cardstatement.py`
- `transactions/migrations/0002_transaction_statement.py`

O que fazem:

- Criam a tabela de `CardStatement`.
- Adicionam o campo `statement` em `Transaction`.

### 4. Admin Django

Arquivos:

- `cards/admin.py`

O que foi feito:

- Registro do model `CardStatement` no Django Admin.
- Configuracao inicial de listagem, filtros, busca e ordenacao para operacao das faturas.

## Servicos implementados

Arquivo:

- `cards/services.py`

### `get_or_create_card_statement`

Responsabilidade:

- Receber um cartao e uma data de compra.
- Identificar a fatura correta com base no dia de fechamento do cartao.
- Criar a fatura quando ela ainda nao existir.
- Definir datas de fechamento e vencimento.
- Herdar a conta de pagamento padrao do cartao.

Regras:

- Compra antes ou no dia de fechamento entra na fatura do mes atual.
- Compra depois do fechamento entra na proxima fatura.
- Apenas cartoes de credito possuem faturas.

### `close_statement`

Responsabilidade:

- Fechar uma fatura aberta.
- Somar as compras vinculadas do tipo `card_purchase`.
- Ignorar transacoes canceladas ou ignoradas.
- Gravar o valor em `closed_amount`.
- Alterar o status para `pending`.

Regra importante:

- Fechar fatura nao altera saldo da conta de pagamento.

### `pay_statement`

Responsabilidade:

- Pagar uma fatura total ou parcialmente.
- Reduzir o saldo da conta de pagamento.
- Atualizar `paid_amount`.
- Alterar status para `paid` ou `partially_paid`.
- Criar uma transacao `statement_payment` vinculada a fatura.

Regra importante:

- O impacto no saldo acontece no pagamento da fatura, nao no fechamento.

### `update_statement_status`

Responsabilidade:

- Atualizar a fatura para `late` quando passou do vencimento e ainda nao houve pagamento total.

## Regra de nao duplicar despesa

Compra no cartao e pagamento de fatura representam eventos financeiros diferentes.

Exemplo:

- Compra no cartao: representa o consumo e deve entrar nos relatorios de despesa por categoria.
- Pagamento da fatura: representa a quitacao da fatura e reduz o saldo da conta de pagamento.

Por isso, `statement_payment` nao deve ser contado como despesa mensal nos seletores de despesa. Essa regra evita duplicidade.

## Testes implementados na fase

### `CardStatement` (model)

Arquivo:

- `cards/tests/test_models.py`

Cobertura:

- Criacao de fatura para cartao de credito.
- Bloqueio de fatura para cartao de beneficio.
- Validacao de mes entre 1 e 12.
- Bloqueio de duas faturas para o mesmo cartao, mes e ano.
- Permissao de conta de pagamento diferente da conta padrao do cartao.

### Vinculo `Transaction` -> `CardStatement`

Arquivo:

- `transactions/tests/test_models.py`

Cobertura:

- Compra no cartao pode ser vinculada a fatura do mesmo cartao.
- Transacao nao pode ser vinculada a fatura de outro cartao.

### Servicos de fatura

Arquivo:

- `cards/tests/test_services.py`

Cobertura:

- Compra antes ou no dia de fechamento entra na fatura do mes atual.
- Compra depois do fechamento entra na proxima fatura.
- Fatura criada herda a conta de pagamento padrao do cartao.
- Fechar fatura soma compras vinculadas e marca como pendente.
- Fechar fatura nao altera saldo da conta de pagamento.
- Pagar fatura reduz saldo da conta de pagamento.
- Pagar fatura cria transacao do tipo `statement_payment`.
- Pagamento parcial marca fatura como parcialmente paga.
- Pagamento total marca fatura como paga.

Execucao local:

```bash
python3 manage.py test cards transactions
```

Ou pelo ambiente Docker:

```bash
docker compose run --rm web python manage.py test cards transactions
```

## Status da fase

Fase 4 concluida (escopo MVP) em 2026-05-12.

O nucleo de faturas foi criado e testado, incluindo model, relacionamento com transacoes, fechamento e pagamento.
Em 2026-05-12, o `CardStatement` foi registrado no admin.

## Backlog pos-fase

- Criar testes para `update_statement_status`.
- Criar seletores de resumo de faturas.
- Avaliar lembretes de vencimento.
- Tratar robustez de concorrencia em pagamento de fatura.
