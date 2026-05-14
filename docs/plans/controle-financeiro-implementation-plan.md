# Plano de Implementação - Controle Financeiro Pessoal

## 1. Estratégia de Desenvolvimento

O projeto será desenvolvido de forma incremental. Cada fase deve gerar uma versão pequena, testável e compreensível.

O foco não é apenas construir o app, mas também praticar:

- Python com boas práticas.
- Django em um projeto real.
- Modelagem de dados.
- Testes automatizados.
- GitFlow profissional.
- Docker e CI/CD.
- Separação entre regra de negócio, persistência e interface.

## 2. GitFlow Definido

Fluxo adotado: **Trunk-Based Development leve**.

| Item | Regra |
| --- | --- |
| Branch principal | `main` |
| Branches de feature | `feature/<descricao-curta>` |
| Branches de correção | `fix/<descricao-curta>` |
| Branches de documentação | `docs/<descricao-curta>` |
| Branches de manutenção | `chore/<descricao-curta>` |
| Commits | Conventional Commits |
| Merge | Via PR com CI verde |
| Tags | Por marcos do roadmap |

Exemplos de branches:

```text
feature/project-foundation
feature/accounts-models
feature/cards-statements
feature/transactions
feature/recurrences
feature/goals
feature/imports
feature/insights
chore/docker-compose
chore/github-actions
docs/readme
```

Exemplos de commits:

```text
feat: add financial account model
test: cover internal transfer rules
fix: prevent card statement payment from duplicating expenses
docs: add architecture overview
chore: configure github actions
refactor: extract statement generation service
```

## 3. Padrão de Trabalho por Tarefa

Para cada tarefa:

1. Escrever a regra em português.
2. Definir o comportamento esperado.
3. Criar ou ajustar os testes.
4. Implementar o menor código possível.
5. Rodar testes localmente.
6. Revisar nomes, responsabilidades e duplicação.
7. Abrir PR.
8. Validar CI.
9. Fazer merge na `main`.

## 4. Arquitetura de Código

Padrão recomendado para cada app Django:

```text
app/
  models.py
  admin.py
  forms.py
  views.py
  urls.py
  services.py
  selectors.py
  tests/
    test_models.py
    test_services.py
    test_selectors.py
```

Quando um arquivo crescer demais, dividir em pacote:

```text
transactions/
  models/
    transaction.py
    transfer.py
  services/
    create_transaction.py
    transfer_money.py
  selectors/
    monthly_summary.py
```

Fluxo principal:

```text
View -> Form -> Service -> Models
Dashboard -> Selector -> Models
Arquivo -> Importer -> Service -> Models
```

## 5. Fase 0 - Preparação do Repositório

### Objetivo

Criar o repositório Git e registrar a documentação inicial.

### Branch

```text
docs/project-spec
```

### Entregáveis

- Inicializar Git.
- Criar `README.md`.
- Criar pasta `docs/`.
- Incluir especificação de design.
- Incluir este plano de implementação.
- Criar `.gitignore`.

### Testes

Ainda não há testes de aplicação nesta fase.

### Critério de pronto

- Repositório inicial criado.
- Documentação versionada.
- `main` criada.
- Primeiro commit feito.

## 6. Fase 1 - Fundação Django, Docker e CI

### Objetivo

Criar a base técnica do projeto.

### Branches sugeridas

```text
feature/project-foundation
chore/docker-compose
chore/github-actions
```

### Entregáveis

- Projeto Django criado.
- App `core` criado.
- Configurações separadas por ambiente, se necessário.
- SQLite configurado.
- Dockerfile.
- Docker Compose.
- GitHub Actions rodando:
  - instalação de dependências;
  - verificação de migrations;
  - testes.
- Estrutura inicial de testes.

### Decisões

- Usar `Decimal` para valores monetários.
- Evitar `float` para dinheiro.
- Usar timezone configurado.
- Configurar idioma e localidade para Brasil.

### Testes

- Teste simples de health check.
- Teste garantindo que a aplicação Django sobe.
- Teste de configuração básica.

### Critério de pronto

- `docker compose up` sobe o app.
- Testes rodam localmente.
- GitHub Actions executa com sucesso.

## 7. Fase 2 - Cadastros Fundamentais

### Objetivo

Criar as entidades base do sistema.

### Branches sugeridas

```text
feature/institutions
feature/accounts-models
feature/cards-models
feature/categories
```

### Models iniciais

- `Institution`
- `FinancialAccount`
- `Card`
- `Category`

### Regras

- Uma conta pertence a uma instituição.
- Uma conta pode ter moeda `BRL`, `USD` ou outra.
- Cartão pode ser `credit`, `benefit`, `transport`, `prepaid`.
- Cartão de crédito tem limite, fechamento, vencimento e conta padrão de pagamento.
- Cartão de benefício tem saldo estimado e não tem fatura tradicional.
- Categorias podem ter hierarquia simples.

### Telas mínimas

- Listar instituições.
- Cadastrar/editar contas.
- Cadastrar/editar cartões.
- Cadastrar/editar categorias.
- Admin Django configurado.

### Testes

- Criar conta com saldo em `Decimal`.
- Criar cartão de crédito com vencimento e fechamento.
- Criar cartão benefício sem fatura obrigatória.
- Validar categoria pai/filha.

### Critério de pronto

- Cadastros funcionam pelo Admin.
- Models têm testes.
- Migrations versionadas.

### Próximos passos imediatos

Status em 2026-05-08: concluídos.

1. [x] Finalizar `Institution` com migration aplicada e testes verdes.
2. [x] Implementar `Category` (`feature/categories`) com model, admin e testes.
3. [x] Implementar `FinancialAccount` (`feature/accounts-models`) com vínculo a `Institution`, moeda e testes.
4. [x] Implementar `Card` (`feature/cards-models`) com tipos e regras mínimas de crédito/benefício, com testes.
5. [x] Revisar documentação da fase e atualizar `README.md` ao concluir a Fase 2.

## 8. Fase 3 - Transações e Transferências

### Objetivo

Criar o núcleo de movimentações financeiras.

### Branches sugeridas

```text
feature/transactions
feature/internal-transfers
```

### Models iniciais

- `Transaction`
- `Transfer`

### Tipos de transação

- Receita.
- Despesa.
- Ajuste.
- Compra no cartão.
- Previsão.
- Pagamento de fatura.

### Regras

- Transferência interna não conta como gasto.
- Transferência interna não conta como receita.
- Transferência reduz saldo da origem.
- Transferência aumenta saldo do destino.
- Toda transação monetária usa `Decimal`.
- Toda transação tem status de pagamento quando aplicável.

### Services

- `create_transaction`
- `transfer_between_accounts`
- `mark_transaction_as_paid`

### Selectors

- `get_account_balance`
- `get_monthly_income_total`
- `get_monthly_expense_total`
- `get_monthly_transfers_total`

### Testes

- Transferir entre duas contas.
- Garantir que transferência não entra no total de gastos.
- Criar despesa pendente.
- Marcar despesa como paga.
- Criar receita.

### Critério de pronto

- Usuário consegue registrar receitas, despesas e transferências.
- Relatórios básicos diferenciam gastos, receitas e transferências.

## 9. Fase 4 - Cartões e Faturas

### Objetivo

Implementar faturas, vencimentos e pagamento por conta.

### Status atual

Status em 2026-05-12: concluída (escopo MVP).

### Branches sugeridas

```text
feature/card-statements
feature/statement-payments
feature/statement-reminders
```

### Models iniciais

- `CardStatement`
- Possível `StatementReminder`, se os lembretes forem persistidos.

### Regras

- Compra no cartão entra na fatura calculada.
- Fatura tem conta de pagamento.
- Conta de pagamento vem do cartão, mas pode ser alterada na fatura.
- Pagamento de fatura reduz saldo da conta de pagamento.
- Pagamento de fatura não duplica despesa por categoria.
- Fatura pode ser paga parcialmente.
- Fatura pode ficar atrasada.

### Status da fatura

- Prevista.
- Pendente.
- Paga parcial.
- Paga.
- Atrasada.
- Cancelada.

### Services

- `get_or_create_statement_for_purchase`
- `close_statement`
- `pay_statement`
- `update_statement_status`
- `generate_statement_reminders`

### Testes

- Compra antes/depois do fechamento vai para fatura correta.
- Fatura herda conta de pagamento do cartão.
- Pagamento total marca fatura como paga.
- Pagamento parcial marca fatura como paga parcial.
- Pagamento de fatura não aumenta despesa do mês.
- Fatura vencida muda para atrasada.

### Critério de pronto

- Cartões de crédito geram faturas.
- Faturas têm vencimento e lembrete.
- Pagamento de fatura altera saldo corretamente.

### Fechamento da fase

Entregue o núcleo previsto para faturas: criação, fechamento, pagamento total/parcial, status e vínculo com transações, com cobertura de testes de model e serviços.

Itens de robustez e evolução permanecem no backlog técnico para ciclos seguintes.

## 10. Fase 5 - Recorrências e Previsões

### Objetivo

Gerar previsões mensais sem marcar pagamento automaticamente.

### Branches sugeridas

```text
feature/recurrences
feature/monthly-forecasts
```

### Models iniciais

- `Recurrence`

### Regras

- Recorrência gera transação prevista.
- Transação prevista não é paga automaticamente.
- Recorrência pode estar ligada a conta ou cartão esperado.
- Usuário pode ignorar uma recorrência no mês.
- Usuário pode cancelar recorrência.
- Valor diferente pode gerar sugestão de revisão.

### Services

- `generate_monthly_recurrence_forecasts`
- `skip_recurrence_for_month`
- `match_recurrence_with_transaction`

### Testes

- Gerar previsão mensal.
- Garantir que previsão não nasce paga.
- Ignorar previsão no mês.
- Reconciliar previsão com transação real.
- Detectar diferença de valor.

### Critério de pronto

- Recorrências aparecem no mês como previsões.
- Usuário confirma, ignora ou ajusta.

### Fechamento da fase

Entregue o núcleo previsto para recorrências e previsões: cadastro de recorrências, geração de transações previstas, listagem mensal, confirmação, ajuste, ignorar previsão, reconciliação inicial e detecção de diferença relevante de valor.

Itens de automação, reconciliação estruturada e frequências avançadas permanecem no backlog técnico para ciclos seguintes.

## 11. Fase 6 - Objetivos e Metas Mensais

### Objetivo

Controlar objetivos de acúmulo e redução.

### Branches sugeridas

```text
feature/goals
feature/monthly-goals
```

### Models iniciais

- `Goal`
- `MonthlyGoal`

### Regras

- Objetivo pode ser de acúmulo ou redução.
- Objetivo pode estar vinculado a uma ou mais contas.
- Meta mensal pode nascer de um objetivo.
- Progresso de acúmulo pode vir do saldo das contas vinculadas.
- Progresso de redução vem de gastos por categoria/período.

### Services

- `calculate_goal_progress`
- `create_monthly_goal_from_goal`
- `update_monthly_goal_status`

### Testes

- Objetivo vinculado a uma conta.
- Objetivo vinculado a múltiplas contas.
- Meta de redução calcula gasto por categoria.
- Meta mensal identifica risco de estouro.

### Critério de pronto

- Usuário consegue criar objetivos.
- Usuário consegue acompanhar metas mensais.

### Fechamento da fase

Entregue o núcleo previsto para objetivos e metas mensais: cadastro de objetivos de acúmulo e redução, metas mensais, progresso por saldos de contas, progresso por despesas de categoria, status de acompanhamento e cobertura automatizada de models e services.

Itens de interface dedicada, seletores para dashboard, acompanhamento proporcional e integração com insights permanecem no backlog técnico para ciclos seguintes.

## 12. Fase 7 - Dashboards e Relatórios

### Objetivo

Criar visualização útil dos dados.

### Status atual

Status em 2026-05-14: concluída (escopo MVP).

### Branches sugeridas

```text
feature/monthly-dashboard
feature/reports
```

### Dashboards iniciais

- Painel mensal.
- Gastos por categoria.
- Contas e patrimônio.
- Cartões e faturas.
- Objetivos e metas.
- Recorrências.
- Lembretes.

### Selectors

- `get_monthly_dashboard`
- `get_category_expense_breakdown`
- `get_account_net_worth`
- `get_card_statement_summary`
- `get_goal_summary`

### Testes

- Dashboard ignora transferências como despesa.
- Dashboard soma gastos por categoria.
- Dashboard mostra faturas pendentes.
- Dashboard calcula patrimônio por moeda.

### Critério de pronto

- Usuário consegue abrir o painel e entender o mês.
- Dados principais aparecem sem precisar entrar no Admin.

### Fechamento da fase

Entregue o núcleo previsto para dashboards e relatórios: app `reports`, selectors para totais mensais, gastos por categoria, patrimônio por moeda, faturas e metas, payload consolidado do dashboard mensal, rota, view, template inicial e cobertura automatizada de selectors e view.

Itens de visualização avançada, filtros, navegação entre meses, gráficos com Chart.js e integração com insights permanecem no backlog técnico para ciclos seguintes.

## 13. Fase 8 - Importações XLSX, CSV e OFX

### Objetivo

Permitir entrada de dados externos com revisão.

### Branches sugeridas

```text
feature/xlsx-import
feature/csv-import
feature/ofx-import
```

### Regras

- Importação nunca confirma tudo automaticamente no MVP.
- Usuário revisa antes de salvar.
- Importador tenta sugerir conta/cartão.
- Importador tenta sugerir categoria.
- Importador evita duplicidade.

### Importers

- `XlsxTransactionImporter`
- `CsvTransactionImporter`
- `OfxTransactionImporter`

### Services

- `stage_imported_transactions`
- `confirm_imported_transaction`
- `discard_imported_transaction`
- `detect_duplicate_transaction`

### Testes

- Importar arquivo de exemplo.
- Normalizar data, valor e descrição.
- Detectar duplicidade.
- Sugerir categoria básica.
- Confirmar transação importada.

### Critério de pronto

- Usuário consegue importar dados e revisar antes de confirmar.

## 14. Fase 9 - Insights e Sugestões Automáticas

### Objetivo

Criar sugestões educativas e aprováveis.

### Branches sugeridas

```text
feature/insights
feature/habit-detection
feature/suggested-goals
```

### Models iniciais

- `Insight`
- Possível `IgnoredPattern`

### Regras

- Sugestão não aplica mudança automaticamente.
- Sugestão pode virar meta mensal.
- Sugestão pode virar recorrência.
- Sugestão pode ser ignorada.
- Sugestão pode ser silenciada.

### Tipos de insight

- Gasto recorrente.
- Categoria em alta.
- Limite sugerido.
- Meta sugerida.
- Fatura próxima do vencimento.
- Saldo baixo em benefício.

### Services

- `detect_recurring_habits`
- `suggest_category_limit`
- `suggest_monthly_goal`
- `approve_insight`
- `ignore_insight`

### Testes

- Detectar padrão semanal.
- Criar sugestão pendente.
- Aprovar sugestão e criar meta.
- Ignorar sugestão sem afetar dados.
- Silenciar padrão.

### Critério de pronto

- O app gera sugestões úteis e o usuário controla o que será aplicado.

## 15. Fase 10 - Taxas, Moeda e Evoluções

### Objetivo

Adicionar dados externos e melhorias avançadas.

### Branches sugeridas

```text
feature/reference-rates
feature/usd-exchange-rate
feature/cdi-estimates
```

### Models iniciais

- `ReferenceRate`

### Regras

- Dólar pode ser atualizado via Banco Central.
- CDI começa manual/configurável.
- Histórico de taxas deve ser salvo.
- Falha de API usa último valor conhecido.
- Rendimento é estimado, não garantia exata.

### Testes

- Salvar taxa manual.
- Buscar último dólar conhecido.
- Calcular saldo estimado em BRL.
- Usar taxa antiga quando atualização falhar.

### Critério de pronto

- Conta em dólar pode ser estimada em reais.
- Porquinho com CDI pode ter rendimento estimado.

## 16. Ordem Recomendada de Estudos Durante o Projeto

### Enquanto faz Fase 1

- Estrutura de projeto Django.
- Docker básico.
- GitHub Actions.
- Settings e variáveis de ambiente.

### Enquanto faz Fase 2

- Django Models.
- Migrations.
- Admin.
- Relacionamentos 1:N e N:N.
- `DecimalField`.

### Enquanto faz Fase 3

- Services.
- Testes unitários.
- Transações financeiras.
- Separação entre receita, despesa e transferência.

### Enquanto faz Fase 4

- Regras de negócio mais complexas.
- Datas.
- Status.
- Testes de cenários.

### Enquanto faz Fase 5

- Jobs e management commands.
- Geração de dados previstos.
- Reconciliação.

### Enquanto faz Fase 6

- Agregações no ORM.
- Modelagem de objetivos.
- Cálculo de progresso.

### Enquanto faz Fase 7

- Selectors.
- Consultas para dashboard.
- Templates.
- Chart.js.

### Enquanto faz Fase 8

- Leitura de arquivos.
- Normalização de dados.
- Tratamento de duplicidade.
- Validação antes de salvar.

### Enquanto faz Fase 9

- Heurísticas.
- Análise de padrões.
- Sugestões aprováveis.
- Design de produto.

## 17. Definition of Done Geral

Uma tarefa só está pronta quando:

- Tem teste para classe ou função criada.
- Usa `Decimal` para valores financeiros.
- Não usa regra de negócio complexa direto na view.
- Tem nomes claros.
- Passa nos testes localmente.
- Passa no GitHub Actions.
- Tem migration revisada, se alterou model.
- Tem documentação curta quando cria uma regra importante.

## 18. Primeira Sequência de Trabalho Recomendada

1. Criar repositório Git.
2. Criar README inicial.
3. Commitar spec e plano.
4. Criar projeto Django.
5. Configurar Docker Compose.
6. Criar GitHub Actions mínimo.
7. Criar app `core`.
8. Criar primeiro teste.
9. Criar app `institutions`.
10. Criar model `Institution`.
11. Criar admin de `Institution`.
12. Criar teste de `Institution`.
