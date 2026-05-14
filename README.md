# Controle Financeiro

Aplicativo web local para controle financeiro pessoal com Django.

## Índice
- [Controle Financeiro](#controle-financeiro)
  - [Índice](#índice)
  - [Visão Geral](#visão-geral)
  - [Stack e Execução](#stack-e-execução)
  - [Fase 1 - Fundação](#fase-1---fundação)
  - [Fase 2 - Cadastros Fundamentais](#fase-2---cadastros-fundamentais)
  - [Fase 3 - Transações e Transferências](#fase-3---transações-e-transferências)
  - [Fase 4 - Cartões e Faturas](#fase-4---cartões-e-faturas)
  - [Fase 5 - Recorrências e Previsões](#fase-5---recorrências-e-previsões)
  - [Fase 6 - Objetivos e Metas Mensais](#fase-6---objetivos-e-metas-mensais)
  - [Fase 7 - Dashboards e Relatórios](#fase-7---dashboards-e-relatórios)
  - [Documentação Detalhada](#documentação-detalhada)
  - [Roadmap](#roadmap)

## Visão Geral

O projeto segue como referencia:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## Stack e Execução

- Linguagem: Python
- Framework: Django
- Banco inicial: SQLite
- Ambiente local: Docker Compose
- CI: GitHub Actions

Comandos base:

```bash
docker compose up --build
```

```bash
python3 manage.py test
```

## Fase 1 - Fundação

Status: concluída

Implementado:

- Projeto Django inicial
- App `core`
- Dockerfile e `docker-compose.yml`
- Workflow de CI inicial
- Health check com teste automatizado

## Fase 2 - Cadastros Fundamentais

Status: concluída

Implementado:

- App `institutions`
- Model `Institution`
- Admin de `Institution`
- Testes de model para `Institution`
- App `categories`
- Model `Category` com hierarquia simples
- Admin de `Category`
- Testes de model para `Category`
- App `accounts`
- Model `FinancialAccount` com vínculo a instituição, tipo, moeda e saldo em `Decimal`
- Admin de `FinancialAccount`
- Testes de model para `FinancialAccount`
- App `cards`
- Model `Card` com regras mínimas para cartões de crédito, benefício, transporte e pré-pago
- Admin de `Card`
- Testes de model para `Card`
- Migrations versionadas para os cadastros fundamentais

## Fase 3 - Transações e Transferências

Status: concluída

Implementado:

- App `transactions`
- Model `Transaction`
- Model `Transfer`
- Admin de `Transaction` e `Transfer`
- Serviços `create_transaction` e `create_transfer`
- Regras para movimentação de saldo por tipo de transação
- Regras para transferências internas entre contas
- Testes de model e serviços para transações e transferências
- Migration versionada para o núcleo de movimentações

## Fase 4 - Cartões e Faturas

Status: concluída

Implementado:

- Model `CardStatement`
- Migration para faturas de cartão
- Vínculo `Transaction.statement`
- Migration para relacionar transações com faturas
- Serviços `get_or_create_card_statement`, `close_statement`, `pay_statement` e `update_statement_status`
- Regras para associar compras no cartão à fatura correta
- Regras para fechamento de fatura sem alteração de saldo
- Regras para pagamento total ou parcial de fatura
- Criação de `statement_payment` ao pagar fatura
- Testes de model e serviços para faturas
- Admin de `CardStatement` no Django Admin

Backlog técnico pós-fase:

- Robustez de concorrência em pagamento de fatura.
- Alinhamento fino entre status de pagamento e impacto em saldo.
- Seletor `get_account_balance` e evoluções de resumo.

Regras importantes:

- Compras no cartão entram na fatura, mas não alteram saldo da conta no momento da compra.
- Fechar a fatura calcula o valor fechado e muda o status, mas não altera saldo.
- Pagar a fatura reduz o saldo da conta de pagamento.
- Pagamento de fatura cria uma transação `statement_payment`, mas essa transação não deve duplicar despesas nos relatórios.

## Fase 5 - Recorrências e Previsões

Status: concluída

Implementado:

- App `recurrences`
- Model `Recurrence`
- Admin de `Recurrence`
- Migration versionada para recorrências
- Serviço `generate_monthly_recurrences_forecasts`
- Serviço `skip_recurrence_for_month`
- Serviço `match_recurrence_with_transaction`
- Serviço `has_relevant_amount_difference`
- Rotas para listar previsões mensais
- Rotas para confirmar, ignorar e ajustar previsões
- Testes de model, serviços e views para recorrências e previsões

Regras importantes:

- Recorrências geram transações previstas (`forecast`), nunca pagas automaticamente.
- Previsões nascem com status `forecasted`.
- Confirmar uma previsão transforma o lançamento em receita ou despesa pendente.
- Ignorar uma previsão marca apenas aquele lançamento como `ignored`.
- Ajustar uma previsão altera o valor previsto e registra a alteração em `notes`.
- Reconciliar uma recorrência com uma transação real registra o vínculo em `notes`.

## Fase 6 - Objetivos e Metas Mensais

Status: concluída

Implementado:

- App `goals`
- Model `Goal`
- Model `MonthlyGoal`
- Admin de `Goal` e `MonthlyGoal`
- Migration versionada para objetivos e metas mensais
- Serviço `calculate_goal_progress`
- Serviço `create_monthly_goal_from_goal`
- Serviço `update_monthly_goal_status`
- Regras para calcular progresso de objetivos de acúmulo
- Regras para calcular progresso de objetivos de redução
- Testes de model e services para objetivos e metas mensais

Regras importantes:

- Objetivos podem ser de acúmulo (`accumulation`) ou redução (`reduction`).
- Objetivos de acúmulo calculam progresso pelo saldo das contas vinculadas.
- Objetivos de redução calculam progresso pelas despesas da categoria no mês.
- Metas mensais podem nascer de um objetivo.
- Metas mensais identificam status `on_track`, `at_risk`, `achieved` e `missed`.
- Transações `forecasted`, `ignored` e `canceled` não entram no cálculo de redução.

## Fase 7 - Dashboards e Relatórios

Status: concluída

Implementado:

- App `reports`
- Selectors para receitas, despesas, gastos por categoria, patrimônio, faturas e metas
- Selector consolidado `get_monthly_dashboard`
- Rota mensal `reports/month/<year>/<month>/`
- View e template do dashboard financeiro mensal
- Testes de selectors e view para relatórios

Regras importantes:

- Transferências internas não entram como receita nem despesa no dashboard.
- Transações `forecasted`, `ignored` e `canceled` ficam fora dos totais principais.
- Pagamentos de fatura não duplicam despesas por categoria.
- Patrimônio considera apenas contas ativas e é agrupado por moeda.

## Documentação Detalhada

Para detalhes técnicos das fases:

- `docs/phases/fase-1-fundacao.md`
- `docs/phases/fase-2-cadastros-fundamentais.md`
- `docs/phases/fase-3-transacoes-e-transferencias.md`
- `docs/phases/fase-4-cartoes-e-faturas.md`
- `docs/phases/fase-5-recorrencias-e-previsoes.md`
- `docs/phases/fase-6-objetivos-e-metas-mensais.md`
- `docs/phases/fase-7-dashboards-e-relatorios.md`

## Roadmap

Os próximos passos seguem o plano de implementação:

- `docs/plans/controle-financeiro-implementation-plan.md`
