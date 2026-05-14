# Fase 7 - Dashboards e Relatorios

## Objetivo da fase

Criar uma visualizacao mensal inicial para consolidar os principais dados financeiros sem exigir que o usuario entre no Django Admin para entender o mes.

Referencias:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## O que foi criado

### 1. App `reports`

Arquivos principais:

- `reports/apps.py`
- `reports/selectors.py`
- `reports/views.py`
- `reports/urls.py`
- `reports/templates/reports/monthly_dashboard.html`
- `reports/tests/test_selectors.py`
- `reports/tests/test_views.py`

Papel do app:

- Centralizar consultas de relatorio e dashboard.
- Expor uma tela mensal com os principais indicadores financeiros.
- Manter regras de agregacao fora da view, usando selectors.

### 2. Selectors de relatorio

Arquivo:

- `reports/selectors.py`

Selectors implementados:

- `get_monthly_income_total`
- `get_monthly_expense_total`
- `get_category_expense_breakdown`
- `get_account_net_worth`
- `get_card_statements`
- `get_goal_summary`
- `get_monthly_dashboard`

Comportamento atual:

- Soma receitas do mes informado.
- Soma despesas do mes informado.
- Ignora transacoes com status `forecasted`, `ignored` e `canceled`.
- Agrupa despesas por categoria.
- Calcula patrimonio por moeda considerando contas ativas.
- Lista faturas de cartao do periodo.
- Lista metas mensais do periodo.
- Monta um payload consolidado para o dashboard mensal.

### 3. View e rota do dashboard mensal

Arquivos:

- `reports/views.py`
- `reports/urls.py`

Rota implementada:

- `reports/month/<int:year>/<int:month>/`

Comportamento:

- Recebe ano e mes pela URL.
- Usa `get_monthly_dashboard` para montar o contexto.
- Renderiza o template `reports/monthly_dashboard.html`.

### 4. Template inicial

Arquivo:

- `reports/templates/reports/monthly_dashboard.html`

O painel exibe:

- Receitas do mes.
- Despesas do mes.
- Saldo do mes.
- Gastos por categoria.
- Patrimonio por moeda.
- Faturas do mes.
- Metas mensais.

## Regras importantes

- Transferencias internas nao entram como receita nem despesa no dashboard.
- Pagamentos de fatura nao entram como despesa mensal por categoria, evitando duplicidade.
- Transacoes previstas, ignoradas e canceladas ficam fora dos totais principais.
- Patrimonio considera apenas contas ativas.

## Testes implementados na fase

### Selectors

Arquivo:

- `reports/tests/test_selectors.py`

Cobertura:

- Soma de receitas do periodo.
- Soma de despesas do periodo.
- Exclusao de transacoes previstas, ignoradas e canceladas.
- Agrupamento de despesas por categoria.
- Calculo de patrimonio por moeda.
- Listagem de faturas por periodo.
- Listagem de metas mensais por periodo.
- Montagem do payload consolidado do dashboard mensal.
- Garantia de que transferencias internas nao afetam os totais de receita e despesa.

### View

Arquivo:

- `reports/tests/test_views.py`

Cobertura:

- Renderizacao do dashboard mensal com sucesso.
- Uso do template correto.
- Exibicao de totais calculados pelos selectors.

Execucao local:

```bash
python3 manage.py test reports
```

Ou pelo ambiente Docker:

```bash
docker compose run --rm web python manage.py test reports
```

## Status da fase

Fase 7 concluida conforme o escopo MVP de dashboards e relatorios.

Itens de evolucao permanecem para ciclos seguintes:

- Graficos com Chart.js.
- Navegacao entre meses.
- Filtros por conta, categoria e cartao.
- Lembretes visuais de faturas vencendo.
- Integracao futura com insights e sugestoes automaticas.
