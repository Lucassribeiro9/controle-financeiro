# Fase 9.1 - Interfaces Operacionais e Parcelamentos

## Objetivo da fase

Consolidar as primeiras interfaces operacionais do sistema e implementar o domínio de parcelamentos.

Esta fase foi registrada como `9.1` porque não fazia parte do plano original como uma fase fechada, mas representa uma evolução importante entre as fases já concluídas:

- cadastros fundamentais;
- transações e transferências;
- cartões e faturas;
- dashboards;
- uso real do sistema fora do Django Admin.

Referências:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## O que foi criado

### 1. Interfaces para contas

Arquivos principais:

- `accounts/forms.py`
- `accounts/selectors.py`
- `accounts/views.py`
- `accounts/urls.py`
- `accounts/templates/accounts/list.html`
- `accounts/templates/accounts/form.html`
- `accounts/templates/accounts/detail.html`

Funcionalidades:

- Listar contas financeiras.
- Criar contas.
- Editar contas.
- Visualizar detalhe de conta.
- Agrupar saldos por moeda.
- Exibir tipo, instituição, saldo e status.

Selectors criados:

- `get_active_accounts`
- `get_accounts_by_currency`
- `get_account_summary`

Regras:

- Nome de conta deve ser único por instituição.
- Validação do formulário também evita duplicidade apenas por diferença de maiúsculas/minúsculas.
- Saldo atual permanece editável neste primeiro CRUD.

### 2. Interfaces para cartões e faturas

Arquivos principais:

- `cards/forms.py`
- `cards/views.py`
- `cards/urls.py`
- `cards/templates/cards/list.html`
- `cards/templates/cards/form.html`
- `cards/templates/cards/statements.html`
- `cards/templates/cards/statement_detail.html`

Funcionalidades de cartões:

- Listar cartões.
- Criar cartão.
- Editar cartão.
- Exibir instituição, tipo, limite, fechamento, vencimento, conta de pagamento e saldo estimado.

Funcionalidades de faturas:

- Listar faturas.
- Detalhar fatura.
- Fechar fatura via POST.
- Pagar fatura via POST.
- Exibir cartão, mês/ano, valores esperado/fechado/pago, status, vencimento e conta de pagamento.

Forms criados:

- `CardForm`
- `StatementPaymentForm`

Regras:

- Cartão de crédito continua exigindo limite, fechamento, vencimento e conta padrão de pagamento.
- Cartão benefício continua exigindo saldo estimado.
- Fatura não é paga com `form.save()`.
- Pagamento de fatura passa por `pay_statement`.
- Fechamento de fatura passa por `close_statement`.
- Listagem e detalhe chamam `update_statement_status`.
- Pagamento reduz saldo da conta e cria `statement_payment`.
- Pagamento de fatura não duplica despesa comum.

### 3. Interfaces para categorias

Arquivos principais:

- `categories/forms.py`
- `categories/views.py`
- `categories/urls.py`
- `categories/templates/categories/list.html`
- `categories/templates/categories/form.html`

Funcionalidades:

- Listar categorias e subcategorias.
- Criar categoria raiz.
- Criar subcategoria.
- Editar categoria.
- Exibir categoria pai, quantidade de subcategorias e status.

Regras:

- Nome de categoria deve ser único.
- Validação do formulário evita duplicidade case-insensitive.
- Categoria pode ser raiz.
- Categoria pode ter categoria pai.
- Categoria não pode ser pai dela mesma.
- A própria categoria é removida das opções de pai durante edição.

### 4. Interfaces para instituições

Arquivos principais:

- `institutions/forms.py`
- `institutions/views.py`
- `institutions/urls.py`
- `institutions/templates/institutions/list.html`
- `institutions/templates/institutions/form.html`
- `institutions/migrations/0002_alter_institution_code.py`

Funcionalidades:

- Listar instituições.
- Criar instituição.
- Editar instituição.
- Exibir nome, razão social, código, status, contas vinculadas e cartões vinculados.

Mudança de model:

- `Institution.code` passou a aceitar `null=True`.

Motivo:

- O código da instituição é opcional.
- Quando não informado, múltiplas instituições devem poder existir sem conflito.
- Quando informado, o código continua único.

Regras:

- Nome de instituição continua obrigatório e único.
- Código informado deve ser único.
- Código vazio é salvo como `NULL`.
- Validações amigáveis evitam erros crus de banco na UI.

### 5. Fluxo próprio para transferências

Arquivos principais:

- `transactions/forms.py`
- `transactions/selectors.py`
- `transactions/views.py`
- `transactions/urls.py`
- `transactions/templates/transactions/transfers.html`
- `transactions/templates/transactions/transfer_form.html`

Form criado:

- `TransferForm`

Views criadas:

- `transfer_list_page`
- `transfer_create_page`

Selector criado:

- `get_transfers_for_period`

Funcionalidades:

- Listar transferências por mês/ano.
- Criar transferência entre contas.
- Exibir origem, destino, valor, data e observações.

Regras:

- Transferência usa o model `Transfer`.
- Transferência é criada via `create_transfer`.
- Transferência não cria `Transaction`.
- Origem e destino devem ser diferentes.
- Valor deve ser positivo.
- Saldo da origem é reduzido.
- Saldo do destino é aumentado.
- Transferência não entra como receita.
- Transferência não entra como despesa.

### 6. App `installments`

Arquivos principais:

- `installments/apps.py`
- `installments/models.py`
- `installments/admin.py`
- `installments/forms.py`
- `installments/services.py`
- `installments/selectors.py`
- `installments/views.py`
- `installments/urls.py`
- `installments/migrations/0001_initial.py`
- `installments/templates/installments/list.html`
- `installments/templates/installments/form.html`
- `installments/templates/installments/detail.html`

Motivo do app próprio:

Parcelamento é um domínio intermediário entre transação, cartão e fatura. Por isso, ele foi separado de `transactions` e `cards`.

### 7. Model `InstallmentPlan`

Arquivo:

- `installments/models.py`

Campos principais:

- `description`
- `total_amount`
- `installment_amount`
- `total_installments`
- `first_installment_date`
- `card`
- `category`
- `status`
- `created_at`
- `updated_at`

Status:

- `active`
- `completed`
- `canceled`

Regras:

- Valor total deve ser maior que zero.
- Valor da parcela deve ser maior que zero.
- Total de parcelas deve ser maior que zero.
- Parcelamento exige cartão de crédito.

### 8. Vínculo entre `Transaction` e parcelamento

Arquivo:

- `transactions/models.py`

Campos adicionados:

- `installment_plan`
- `installment_number`

Migration:

- `transactions/migrations/0003_transaction_installment_plan.py`

Regras:

- Transação vinculada a parcelamento deve ser `card_purchase`.
- O cartão da transação deve ser o mesmo cartão do plano.
- Parcela vinculada a um plano deve ter número da parcela.
- Número da parcela não pode superar o total de parcelas do plano.

### 9. Services de parcelamento

Arquivo:

- `installments/services.py`

Services criados:

- `create_installment_plan`
- `generate_installment_transactions`
- `cancel_installment_plan`
- `get_installment_progress`

#### `create_installment_plan`

Responsabilidade:

- Criar o plano de parcelamento.
- Calcular o valor base da parcela.
- Validar o plano.
- Gerar as transações de parcelas.

#### `generate_installment_transactions`

Responsabilidade:

- Gerar N transações `card_purchase`.
- Vincular cada transação ao plano.
- Definir `installment_number`.
- Definir a fatura correta de cada parcela usando `get_or_create_card_statement`.
- Impedir geração duplicada para um plano que já tem parcelas.

Regras:

- A soma das parcelas deve fechar com o valor total.
- A última parcela ajusta diferenças de centavos.
- Parcelas não alteram saldo da conta no momento da geração.

#### `cancel_installment_plan`

Responsabilidade:

- Marcar o plano como `canceled`.
- Não apagar parcelas já geradas.

Regra:

- Plano concluído não pode ser cancelado.

#### `get_installment_progress`

Responsabilidade:

- Retornar quantidade de parcelas geradas.
- Retornar quantidade de parcelas pagas.
- Retornar quantidade restante.
- Retornar valor total gerado.

### 10. Selectors de parcelamento

Arquivo:

- `installments/selectors.py`

Selectors criados:

- `get_active_installment_plans`
- `get_installment_plan_detail`
- `get_installments_by_card`
- `get_installments_ending_soon`

### 11. Telas de parcelamento

Rotas:

- `GET /installments/`
- `GET|POST /installments/create/`
- `GET /installments/<id>/`
- `POST /installments/<id>/cancel/`

Telas:

- Lista de parcelamentos ativos.
- Formulário de criação.
- Detalhe do parcelamento.
- Cancelamento via POST.

## Integração visual

Arquivos principais:

- `templates/base.html`
- `templates/partials/sidebar.html`
- `templates/partials/messages.html`
- `static/css/app.css`

O menu lateral passou a incluir acessos para:

- Contas
- Cartões
- Categorias
- Instituições
- Lançamentos
- Transferências
- Parcelamentos
- Insights
- Importações
- Recorrências

## Testes implementados na fase

### Contas

Arquivos:

- `accounts/tests/test_selectors.py`
- `accounts/tests/test_views.py`

Cobertura:

- Listagem de contas.
- Criação de conta.
- Edição de conta.
- Validação de nome único por instituição.
- Agrupamento por moeda.

### Cartões e faturas

Arquivo:

- `cards/tests/test_views.py`

Cobertura:

- Listagem de cartões.
- Criação de cartão de crédito.
- Criação de cartão benefício.
- Edição de cartão.
- Listagem de faturas.
- Detalhe de fatura.
- Pagamento via POST.
- Redução de saldo.
- Garantia de não duplicar despesa.

### Categorias

Arquivo:

- `categories/tests/test_views.py`

Cobertura:

- Listagem de categorias.
- Criação de categoria raiz.
- Criação de subcategoria.
- Edição de categoria.
- Bloqueio de nome duplicado.
- Exibição de quantidade de subcategorias.

### Instituições

Arquivo:

- `institutions/tests/test_views.py`

Cobertura:

- Listagem de instituições.
- Criação de instituição.
- Edição de instituição.
- Validação de nome único.
- Validação de código único quando informado.
- Múltiplas instituições sem código.
- Contagem de contas e cartões vinculados.

### Transferências

Arquivos:

- `transactions/tests/test_views.py`
- `transactions/tests/test_selectors.py`

Cobertura:

- Listagem de transferências.
- Criação de transferência.
- Atualização correta de saldos.
- Rejeição de origem e destino iguais.
- Garantia de que transferência não cria `Transaction`.
- Garantia de que transferência não afeta totais mensais de receita/despesa.

### Parcelamentos

Arquivos:

- `installments/tests/test_services.py`
- `installments/tests/test_selectors.py`
- `installments/tests/test_views.py`

Cobertura:

- Criação de parcelamento de 10x.
- Geração de 10 transações.
- Associação de parcelas à fatura correta.
- Soma das parcelas igual ao valor total.
- Ajuste de centavos na última parcela.
- Garantia de que compra parcelada não vira recorrência.
- Cancelamento preservando parcelas geradas.
- Bloqueio de cancelamento de plano concluído.
- Selectors de listagem, detalhe, cartão e próximos do fim.
- Views de listagem, criação, detalhe e cancelamento.

## Execução local

```bash
python3 manage.py test
```

Ou usando o ambiente virtual local:

```bash
venv/bin/python manage.py test
```

## Status da fase

Fase 9.1 concluída em 2026-05-20.

Foram entregues as interfaces operacionais iniciais e o domínio de parcelamentos com cobertura automatizada. O sistema passou a permitir operar os principais cadastros e fluxos financeiros sem depender exclusivamente do Django Admin.

## Backlog pós-fase

- Melhorar UX dinâmica dos forms de cartão conforme o tipo selecionado.
- Criar edição controlada de parcelamentos.
- Definir política explícita para cancelamento de parcelas futuras.
- Integrar parcelamentos ao dashboard mensal.
- Criar visualizações mais ricas para progresso de parcelamentos.
- Criar filtros por cartão, status e período nas telas de parcelamentos.
- Evoluir tratamento de saldo inicial para ajuste de saldo em vez de edição direta.
