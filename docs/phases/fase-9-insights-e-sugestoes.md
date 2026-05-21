# Fase 9 - Insights e Sugestoes Automaticas

## Objetivo da fase

Criar a primeira camada de sugestoes educativas do app, sempre com controle do usuario antes de qualquer mudanca real.

O app passa a observar dados financeiros ja cadastrados e gerar insights pendentes. Esses insights podem ser aprovados, ignorados ou silenciados. A regra principal da fase e simples:

> Insight nao e acao automatica. Insight e uma sugestao aguardando decisao do usuario.

Referencias:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## O que foi criado

### 1. App `insights`

Arquivos principais:

- `insights/apps.py`
- `insights/models.py`
- `insights/admin.py`
- `insights/services.py`
- `insights/selectors.py`
- `insights/views.py`
- `insights/urls.py`
- `insights/migrations/0001_initial.py`
- `insights/migrations/0002_rename_source_insight_source_key.py`
- `insights/tests/test_models.py`
- `insights/tests/test_services.py`
- `insights/tests/test_selectors.py`
- `insights/tests/test_views.py`

Papel do app:

- Centralizar sugestoes automaticas e habitos detectados.
- Guardar sugestoes pendentes para revisao.
- Permitir que o usuario aprove, ignore ou silencie sugestoes.
- Criar metas mensais apenas depois de aprovacao explicita.
- Evitar sugestoes duplicadas no mesmo mes.
- Evitar sugestoes futuras quando um padrao for silenciado.

### 2. Model `Insight`

Arquivo:

- `insights/models.py`

Papel do model:

- Representar uma sugestao gerada pelo sistema.
- Guardar titulo, mensagem, tipo e status da sugestao.
- Guardar valor sugerido quando aplicavel.
- Guardar vinculos opcionais com categoria, recorrencia e meta mensal.
- Guardar `source_key` para rastrear a origem da sugestao e evitar duplicidade.

Campos principais:

- `title`
- `message`
- `insight_type`
- `status`
- `suggested_amount`
- `category`
- `recurrence`
- `monthly_goal`
- `source_key`
- `created_at`
- `updated_at`

Tipos de insight:

- `recurring_expense`
- `category_limit`
- `monthly_goal`
- `bill_reminder`
- `low_balance`

Status:

- `pending`
- `approved`
- `ignored`
- `silenced`

Regras iniciais:

- Insight de limite de categoria exige categoria vinculada.
- Valor sugerido, quando informado, deve ser maior que zero.
- Insights nascem como `pending` por padrao.

### 3. Model `IgnoredPattern`

Arquivo:

- `insights/models.py`

Papel do model:

- Guardar padroes que o usuario nao quer receber novamente.
- Evitar que o app repita sugestoes semelhantes em meses futuros.

Campos principais:

- `pattern_key`
- `reason`
- `created_at`

Exemplos de `pattern_key`:

```text
category-limit:5
habit-category:8
```

Diferença entre `source_key` e `pattern_key`:

- `source_key` identifica uma sugestao especifica de um mes.
- `pattern_key` identifica o padrao geral que pode ser silenciado.

Exemplo:

```text
source_key: category-limit:5:2026-05
pattern_key: category-limit:5
```

### 4. Admin

Arquivo:

- `insights/admin.py`

Models registrados:

- `Insight`
- `IgnoredPattern`

Comportamento:

- Permite consultar insights por tipo, status e categoria.
- Permite buscar por titulo, mensagem e `source_key`.
- Permite consultar padroes silenciados por `pattern_key` e motivo.

### 5. Services

Arquivo:

- `insights/services.py`

Services implementados:

- `get_category_expense_total`
- `suggest_category_limit`
- `approve_insight`
- `ignore_insight`
- `silence_insight`
- `detect_recurrent_habits`

Funcoes auxiliares:

- `_build_monthly_source_key`
- `_build_pattern_key`
- `_get_pattern_key_from_source_key`

#### `get_category_expense_total`

Calcula o total gasto em uma categoria em um mes.

Regras:

- Considera apenas transacoes do tipo `expense`.
- Considera apenas transacoes pagas.
- Ignora transacoes `canceled`, `ignored` e `forecasted`.

#### `suggest_category_limit`

Cria uma sugestao de limite para uma categoria com gasto no mes.

Exemplo de insight criado:

```text
Titulo: Limite sugerido para Alimentacao
Tipo: category_limit
Status: pending
Valor sugerido: total gasto na categoria no mes
```

Regras:

- Nao cria insight se o total da categoria for zero.
- Nao cria insight duplicado para a mesma categoria no mesmo mes.
- Nao cria insight se o padrao da categoria estiver silenciado.
- Nao cria meta automaticamente.

#### `approve_insight`

Aprova um insight pendente.

No MVP, a aprovacao de insight `category_limit`:

1. Cria um `Goal` do tipo `reduction`.
2. Cria uma `MonthlyGoal` a partir desse objetivo.
3. Vincula a meta mensal criada ao insight.
4. Marca o insight como `approved`.

Regra importante:

- A meta so nasce depois da aprovacao.

#### `ignore_insight`

Marca um insight como `ignored`.

Regras:

- Nao cria objetivo.
- Nao cria meta mensal.
- Nao altera transacoes.
- Afeta apenas aquela sugestao.

#### `silence_insight`

Marca um insight como `silenced` e cria um `IgnoredPattern`.

Regras:

- Usa o `source_key` para extrair uma `pattern_key` generica.
- Evita sugestoes futuras do mesmo padrao.
- Nao cria objetivo.
- Nao cria meta mensal.

#### `detect_recurrent_habits`

Detecta categorias com tres ou mais despesas pagas no mesmo mes.

Comportamento atual:

- Agrupa despesas por categoria.
- Cria insight `recurring_expense` quando encontra recorrencia simples.
- Usa a media dos gastos como `suggested_amount`.
- Evita duplicidade mensal por `source_key`.
- Respeita padroes silenciados por `IgnoredPattern`.

Observacao:

- Esta e uma heuristica inicial, simples e testavel. Ela pode evoluir depois para considerar descricao, dia da semana, estabelecimento e historico entre meses.

### 6. Selectors

Arquivo:

- `insights/selectors.py`

Selectors implementados:

- `get_pending_insights`
- `get_insights_by_status`
- `get_recent_insights`
- `get_ignored_patterns`

Comportamento:

- `get_pending_insights` lista sugestoes aguardando decisao.
- `get_insights_by_status` permite filtrar por status.
- `get_recent_insights` lista historico curto para telas ou dashboard.
- `get_ignored_patterns` lista padroes silenciados.

### 7. Views e rotas

Arquivos:

- `insights/views.py`
- `insights/urls.py`

Rotas implementadas:

- `GET /insights/`
- `GET /insights/?status=<status>`
- `GET /insights/recent/?limit=<limit>`
- `POST /insights/<int:insight_id>/approve/`
- `POST /insights/<int:insight_id>/ignore/`
- `POST /insights/<int:insight_id>/silence/`

Fluxo:

1. Service cria insights pendentes.
2. Usuario lista insights em `/insights/`.
3. Usuario decide aprovar, ignorar ou silenciar.
4. A view chama o service correspondente.
5. A resposta JSON retorna o estado atualizado.

Exemplo de resposta:

```json
{
  "id": 1,
  "title": "Limite sugerido para Alimentacao",
  "message": "Criar meta para acompanhar alimentacao.",
  "insight_type": "category_limit",
  "status": "pending",
  "suggested_amount": "500.00",
  "category_id": 3,
  "recurrence_id": null,
  "monthly_goal_id": null,
  "source_key": "category-limit:3:2026-05",
  "created_at": "2026-05-15T12:00:00+00:00"
}
```

## Regras importantes

- Sugestoes nao aplicam mudancas automaticamente.
- O usuario controla aprovar, ignorar ou silenciar.
- Aprovar um limite de categoria cria `Goal` e `MonthlyGoal`.
- Ignorar afeta apenas o insight selecionado.
- Silenciar cria um padrao ignorado para evitar repeticao futura.
- `source_key` evita duplicidade no mesmo mes.
- `pattern_key` evita repeticao do mesmo padrao nos meses seguintes.
- Services concentram regras de negocio.
- Selectors concentram consultas reutilizaveis.
- Views apenas orquestram request, service e resposta JSON.

## Testes implementados na fase

### Models

Arquivo:

- `insights/tests/test_models.py`

Cobertura:

- Criacao de insight de limite por categoria.
- Validacao de categoria obrigatoria para limite de categoria.
- Validacao de valor sugerido positivo.
- Retorno textual de `Insight`.
- Criacao de `IgnoredPattern`.
- Unicidade de `pattern_key`.

### Services

Arquivo:

- `insights/tests/test_services.py`

Cobertura:

- Calculo de gasto por categoria ignorando transacoes previstas.
- Criacao de insight pendente de limite de categoria.
- Prevencao de insight duplicado no mesmo mes.
- Respeito a padroes silenciados.
- Aprovacao criando `Goal` e `MonthlyGoal`.
- Ignorar insight sem criar meta.
- Silenciar insight criando `IgnoredPattern`.
- Deteccao inicial de habito recorrente por categoria.

### Selectors

Arquivo:

- `insights/tests/test_selectors.py`

Cobertura:

- Listagem de insights pendentes.
- Filtro por status.
- Limite de insights recentes.
- Listagem de padroes silenciados.

### Views

Arquivo:

- `insights/tests/test_views.py`

Cobertura:

- Listagem de insights pendentes.
- Filtro por status na listagem.
- Listagem de insights recentes com limite.
- Rejeicao de limite invalido.
- Aprovacao de insight via endpoint.
- Ignorar insight via endpoint.
- Silenciar insight via endpoint.

Execucao local:

```bash
python3 manage.py test insights
```

Ou pelo ambiente Docker:

```bash
docker compose run --rm web python manage.py test insights
```

## Validacao da fase

Comandos executados no ambiente Docker:

```bash
docker compose run --rm web python manage.py check
```

Resultado:

```text
System check identified no issues (0 silenced).
```

```bash
docker compose run --rm web python manage.py makemigrations --check --dry-run
```

Resultado:

```text
No changes detected
```

```bash
docker compose run --rm web python manage.py test insights
```

Resultado:

```text
Found 25 test(s).
OK
```

```bash
docker compose run --rm web python manage.py test
```

Resultado:

```text
Found 165 test(s).
OK
```

## Status da fase

Fase 9 concluida conforme o escopo MVP de insights e sugestoes automaticas.

Itens de evolucao permanecem para ciclos seguintes:

- Sugerir recorrencias a partir de padroes detectados.
- Criar insights de faturas proximas do vencimento.
- Criar insights de saldo baixo em cartoes de beneficio.
- Integrar insights ao dashboard mensal.
- Melhorar heuristicas usando descricao, dia da semana e historico entre meses.
- Permitir edicao de valor sugerido antes da aprovacao.
