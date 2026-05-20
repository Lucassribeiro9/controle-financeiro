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
  - [Fase 8 - Importações XLSX, CSV e OFX](#fase-8---importações-xlsx-csv-e-ofx)
  - [Fase 9 - Insights e Sugestões Automáticas](#fase-9---insights-e-sugestões-automáticas)
  - [Fase 9.1 - Interfaces Operacionais e Parcelamentos](#fase-91---interfaces-operacionais-e-parcelamentos)
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

## Fase 8 - Importações XLSX, CSV e OFX

Status: concluída

Implementado:

- App `imports`
- Model `ImportedTransaction`
- Admin de `ImportedTransaction`
- Migration versionada para importações
- Importers `CsvTransactionImporter`, `XlsxTransactionImporter` e `OfxTransactionImporter`
- Dataclass `ImportedTransactionRow` para normalização comum dos formatos
- Service `stage_imported_transactions`
- Service `confirm_imported_transaction`
- Service `discard_imported_transaction`
- Services de hash e detecção de duplicidade
- Selector `get_imported_transactions_for_review`
- Rotas para upload, revisão, confirmação e descarte
- Testes de importers, services, selectors e views

Regras importantes:

- Importações não viram transações reais automaticamente.
- Linhas importadas entram como pendentes para revisão.
- Valores negativos são tratados como despesas sugeridas.
- Valores positivos são tratados como receitas sugeridas.
- CSV, XLSX e OFX são normalizados para o mesmo formato interno.
- OFX usa `FITID` como `external_id` quando disponível.
- Duplicidades podem ser identificadas por `external_id` ou `import_hash`.
- Confirmar uma importação cria uma `Transaction` real usando o fluxo existente de transações.

## Fase 9 - Insights e Sugestões Automáticas

Status: concluída

Implementado:

- App `insights`
- Model `Insight`
- Model `IgnoredPattern`
- Admin de `Insight` e `IgnoredPattern`
- Migrations versionadas para insights e padrões silenciados
- Service `get_category_expense_total`
- Service `suggest_category_limit`
- Service `detect_recurrent_habits`
- Service `approve_insight`
- Service `ignore_insight`
- Service `silence_insight`
- Selectors para insights pendentes, por status, recentes e padrões silenciados
- Rotas para listar, aprovar, ignorar e silenciar insights
- Testes de models, services, selectors e views

Regras importantes:

- Insights nascem como sugestões pendentes.
- Insights não aplicam mudanças automaticamente.
- Aprovar um insight de limite de categoria cria um objetivo de redução e uma meta mensal.
- Ignorar um insight não altera metas, recorrências nem transações.
- Silenciar um insight cria um padrão ignorado para evitar sugestões futuras semelhantes.
- `source_key` evita duplicidade mensal de sugestões.

## Fase 9.1 - Interfaces Operacionais e Parcelamentos

Status: concluída

Implementado:

- Primeiras interfaces HTML para contas, cartões, faturas, categorias e instituições.
- Fluxo próprio de transferências entre contas, separado de `Transaction`.
- App `installments` para domínio de parcelamentos.
- Model `InstallmentPlan`.
- Vínculo de `Transaction` com `installment_plan` e `installment_number`.
- Services para criar, gerar parcelas, cancelar e acompanhar progresso de parcelamentos.
- Selectors para listar parcelamentos ativos, por cartão, detalhe e próximos do fim.
- Templates, forms, views e rotas para parcelamentos.
- Templates, forms, views e rotas para os principais cadastros operacionais.
- Testes de views, selectors, services e regras de domínio para os fluxos criados.

Regras importantes:

- Transferência usa `Transfer` e `create_transfer`, não uma `Transaction` comum.
- Transferências não entram nos totais mensais de receitas ou despesas.
- Pagamento de fatura continua passando por `pay_statement`.
- Parcelamento é uma compra única representada por `InstallmentPlan`.
- Parcelamento gera N transações `card_purchase`, uma para cada parcela.
- Cada parcela é associada à fatura correta do cartão.
- A soma das parcelas fecha exatamente com o valor total.
- A última parcela ajusta diferenças de centavos.
- Cancelar parcelamento não apaga parcelas já geradas.

## Documentação Detalhada

Para detalhes técnicos das fases:

- `docs/phases/fase-1-fundacao.md`
- `docs/phases/fase-2-cadastros-fundamentais.md`
- `docs/phases/fase-3-transacoes-e-transferencias.md`
- `docs/phases/fase-4-cartoes-e-faturas.md`
- `docs/phases/fase-5-recorrencias-e-previsoes.md`
- `docs/phases/fase-6-objetivos-e-metas-mensais.md`
- `docs/phases/fase-7-dashboards-e-relatorios.md`
- `docs/phases/fase-8-importacoes-xlsx-csv-ofx.md`
- `docs/phases/fase-9-insights-e-sugestoes.md`
- `docs/phases/fase-9-1-interfaces-operacionais-e-parcelamentos.md`

## Roadmap

Os próximos passos seguem o plano de implementação:

- `docs/plans/controle-financeiro-implementation-plan.md`
