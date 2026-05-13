# Fase 6 - Objetivos e Metas Mensais

## Objetivo da fase

Implementar o fluxo inicial de objetivos financeiros e metas mensais, permitindo acompanhar objetivos de acumulo e reducao com progresso calculado automaticamente a partir de saldos de contas ou despesas por categoria.

Referencias:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## O que foi criado

### 1. App `goals`

Arquivos principais:

- `goals/apps.py`
- `goals/models.py`
- `goals/services.py`
- `goals/admin.py`
- `goals/tests/test_models.py`
- `goals/tests/test_services.py`
- `goals/migrations/0001_initial.py`

Papel do app:

- Centralizar objetivos financeiros.
- Permitir metas mensais derivadas de objetivos.
- Calcular progresso de acumulo e reducao.
- Identificar status inicial de acompanhamento mensal.

### 2. Model `Goal`

Arquivo principal:

- `goals/models.py`

Campos principais:

- `name`
- `goal_type`
- `target_amount`
- `start_date`
- `target_date`
- `is_active`
- `accounts`
- `category`

Tipos iniciais:

- `accumulation`
- `reduction`

Regras iniciais:

- Valor alvo deve ser positivo.
- Objetivo de reducao exige categoria vinculada.
- Data alvo, quando informada, deve ser posterior a data de inicio.
- Objetivo pode estar vinculado a uma ou mais contas financeiras.

Uso esperado:

- Objetivos de acumulo usam contas vinculadas para calcular progresso.
- Objetivos de reducao usam categoria para calcular gasto no periodo.

### 3. Model `MonthlyGoal`

Arquivo principal:

- `goals/models.py`

Campos principais:

- `goal`
- `year`
- `month`
- `target_amount`
- `current_amount`
- `status`

Status iniciais:

- `on_track`
- `at_risk`
- `achieved`
- `missed`

Regras iniciais:

- Valor alvo deve ser positivo.
- Valor atual nao pode ser negativo.
- Mes deve estar entre 1 e 12.
- Meta mensal deve estar vinculada a um objetivo.
- Deve existir apenas uma meta por objetivo, ano e mes.

### 4. Admin Django

Arquivo:

- `goals/admin.py`

O que foi feito:

- Registro do model `Goal` no Django Admin.
- Registro do model `MonthlyGoal` no Django Admin.
- Configuracao inicial de listagem, filtros e busca para objetivos e metas mensais.

## Servicos implementados

Arquivo:

- `goals/services.py`

### `calculate_goal_progress`

Responsabilidade:

- Calcular o progresso de um objetivo financeiro.
- Retornar valor atual, valor alvo, valor restante e percentual de progresso.

Regras para objetivos de acumulo:

- Soma o saldo das contas vinculadas ao objetivo.
- Compara o saldo total com o valor alvo do objetivo.

Regras para objetivos de reducao:

- Exige ano e mes para calcular o periodo.
- Soma as despesas da categoria vinculada no mes informado.
- Ignora transacoes com status `forecasted`, `ignored` e `canceled`.

### `create_monthly_goal_from_goal`

Responsabilidade:

- Criar uma meta mensal a partir de um objetivo.
- Usar o valor alvo do objetivo quando nenhum valor mensal especifico for informado.
- Validar a meta mensal antes de salvar.

### `update_monthly_goal_status`

Responsabilidade:

- Atualizar o valor atual da meta mensal.
- Atualizar o status conforme o tipo do objetivo.

Regras para objetivos de acumulo:

- `achieved` quando o valor atual alcanca ou supera a meta mensal.
- `on_track` enquanto o valor atual ainda esta abaixo da meta mensal.

Regras para objetivos de reducao:

- `missed` quando o gasto atual alcanca ou supera o limite.
- `at_risk` quando o gasto atual alcanca pelo menos 80% do limite.
- `on_track` enquanto o gasto atual esta abaixo de 80% do limite.

## Fluxo atual de objetivos e metas

1. Um objetivo e cadastrado no Admin como acumulo ou reducao.
2. Objetivos de acumulo podem receber contas vinculadas.
3. Objetivos de reducao recebem uma categoria vinculada.
4. Uma meta mensal pode ser criada a partir do objetivo.
5. O servico calcula o progresso automaticamente.
6. A meta mensal recebe valor atual e status de acompanhamento.

## Testes implementados na fase

### `Goal` (model)

Arquivo:

- `goals/tests/test_models.py`

Cobertura:

- Criacao de objetivo de acumulo com conta vinculada.
- Criacao de objetivo de reducao com categoria vinculada.
- Validacao de valor alvo positivo.
- Exigencia de categoria para objetivo de reducao.
- Validacao de data alvo posterior a data de inicio.
- Validacao de `__str__`.

### `MonthlyGoal` (model)

Arquivo:

- `goals/tests/test_models.py`

Cobertura:

- Criacao de meta mensal vinculada a objetivo.
- Validacao de mes entre 1 e 12.
- Validacao de valor alvo positivo.
- Bloqueio de valor atual negativo.
- Bloqueio de duplicidade para mesmo objetivo, ano e mes.
- Validacao de `__str__`.

### Servicos de objetivos e metas

Arquivo:

- `goals/tests/test_services.py`

Cobertura:

- Calculo de progresso de acumulo usando saldo de contas vinculadas.
- Calculo de progresso de reducao usando despesas da categoria no mes.
- Ignorar transacoes previstas, ignoradas e canceladas no progresso de reducao.
- Exigencia de ano e mes para objetivos de reducao.
- Criacao de meta mensal a partir de objetivo.
- Atualizacao de status para `achieved`.
- Atualizacao de status para `at_risk`.
- Atualizacao de status para `missed`.

Execucao local:

```bash
python3 manage.py test goals
```

Ou pelo ambiente Docker:

```bash
docker compose run --rm web python manage.py test goals
```

## Status da fase

Fase 6 concluida (escopo MVP) em 2026-05-13.

O nucleo de objetivos e metas mensais foi criado e testado, incluindo model, admin, migrations, services e cobertura automatizada para as regras principais.

## Backlog pos-fase

- Criar telas fora do Admin para gerenciar objetivos e metas.
- Criar seletores de resumo para uso nos dashboards.
- Evoluir status de metas mensais com acompanhamento proporcional ao dia do mes.
- Suportar aportes manuais independentes de saldo de conta.
- Integrar objetivos e metas aos insights e sugestoes automaticas.
