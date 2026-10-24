# Spec 011 - Insights: Geracao e Criterios de Aceite

## Contexto

O modulo de Insights (Fase 9) guarda sugestoes que o usuario aprova, ignora ou silencia, mas nada no codigo de producao dispara os geradores: `suggest_category_limit` e `detect_recurrent_habits` so rodavam nos testes. A validacao com o banco local (170 transacoes, 144 sem categoria) tambem expos que transacoes sem categoria geravam o titulo "Habito recorrente em None".

## Objetivo

Tornar a geracao executavel, corrigir os defeitos encontrados e documentar regras e criterios de exibicao de cada tipo de insight.

## Fora de Escopo

- Geradores de `monthly_goal`, `bill_reminder` e `low_balance`.
- Botao na UI, mudanca de layout ou navegacao, edicao do valor sugerido antes da aprovacao.
- Agendamento automatico (cron), command de seed e fixtures.

## Estado Atual

- `Insight` tem 5 tipos, mas so `category_limit` e `recurring_expense` possuem gerador.
- Aprovar `category_limit` reutiliza o `Goal` de reducao da categoria (cria so se nao existir) e cria o `MonthlyGoal` no mes corrente (`timezone.localdate()`), nao no mes do insight. A aprovacao e atomica e idempotente (FIN-41).
- Insight aprovado nao pode ser ignorado nem silenciado (`ValidationError`, mapeado para message na view; ADR-010).
- Se ja existe `MonthlyGoal` da categoria no mes com valor diferente do sugerido, a view mostra a comparacao e pergunta se altera ou mantem; com o mesmo valor, apenas vincula ao insight.
- A FK `Insight.category` e `SET_NULL`; aprovar um `category_limit` cuja categoria foi removida quebrava com `AttributeError`.

## Comportamento Esperado

- `python manage.py generate_insights [--year AAAA --month MM]` gera os insights do mes (padrao: mes corrente) e informa quantos foram criados.
- A geracao e idempotente: rodar de novo no mesmo mes cria 0.
- Insight nunca aplica mudanca sozinho; so a aprovacao explicita cria meta.

## Regras de Negocio

### Gasto considerado

- Definicao unica em `transactions/constants.py` (#211), compartilhada com goals, reports, home e categorias: `expense`, `card_purchase` e `benefit_purchase`, pela data da compra, exceto `canceled`, `ignored` e `forecasted`. Pendentes, atrasados e parcialmente pagos contam.
- Insights exige ainda categoria e o mes informado.
- Ficam fora: sem categoria, `statement_payment` (a compra no cartao ja foi contada), transferencias e receitas.
- O `Goal` de reducao criado na aprovacao usa a mesma definicao, entao o progresso da meta e o limite sugerido batem para o mesmo mes.
- Metas existentes: sem backfill. `MonthlyGoal.current_amount` e `status` sao recalculados quando a pagina de metas do periodo e aberta, entao meses passados podem mudar de status ao serem reabertos.

### Criterios por tipo

| Tipo | Gerado? | Condicao | Valor sugerido | Ao aprovar |
| --- | --- | --- | --- | --- |
| `category_limit` | Sim | categoria com gasto > 0 no mes | total do mes (2 casas) | cria `Goal` de reducao + `MonthlyGoal` |
| `recurring_expense` | Sim | categoria com 3 ou mais gastos no mes | media (0,01, ROUND_HALF_UP) | apenas registra a decisao |
| `monthly_goal` | Nao | - | - | - |
| `bill_reminder` | Nao | - | - | - |
| `low_balance` | Nao | - | - | - |

### Duplicidade e silenciamento

- `source_key` (`<prefixo>:<categoria>:<AAAA-MM>`) impede o mesmo insight duas vezes no mes.
- `IgnoredPattern` (`<prefixo>:<categoria>`) impede o tipo correspondente em meses futuros. Silenciar um tipo nao silencia o outro.
- Uma categoria pode receber `category_limit` e `recurring_expense` no mesmo mes.

### Exibicao

- A mensagem mostra valores em BRL (`R$ 1.234,56`) e o mes por extenso (ex.: "Maio/2026"), nunca "neste mes".
- A pagina `/insights/page/` lista apenas insights `pending`.

## Dados, Services e Selectors

- Service `generate_monthly_insights(*, year, month)` em `insights/services.py` retorna a lista de insights criados.
- Filtro unico de gasto qualificado em `_qualifying_expenses(*, year, month)`.
- Command `insights/management/commands/generate_insights.py` apenas orquestra o service.
- Sem selector novo.

## Schema

**Esta spec nao muda schema.** Nenhuma migration esperada.

## Estados de Erro

- `--month` fora de 1 a 12: `CommandError`.
- Banco sem despesas qualificadas: 0 insights, sem erro.
- Aprovar `category_limit` com categoria removida: `ValidationError` (mapeado para message na view), insight segue `pending`.

## Testes Esperados

- Service sobre cenario realista (`insights/tests/scenarios.py`): inclusao, exclusao, mes seguinte, idempotencia, `IgnoredPattern`, banco vazio, arredondamento da media, formato da mensagem, aprovacao com categoria removida.
- Command: argumentos, padrao do mes corrente, mes invalido.
- View: aprovar com categoria removida redireciona com message, sem 500.
- Validacao manual no banco local, registrando so contagens e resultados.

## Criterios de Aceite

- Cada tipo gerado tem condicao, valor e efeito de aprovacao documentados acima.
- O cenario realista gera `category_limit` e `recurring_expense` apenas para o que qualifica.
- Rodar a geracao duas vezes nao duplica insights.
- Nenhum titulo ou mensagem contem "None".
- `python manage.py makemigrations --check --dry-run` nao detecta mudancas.

## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Open Questions

- Aprovar usa o mes corrente para a meta, e nao o mes do insight. Aprovar em junho um insight de maio cria a meta de junho. Manter ou usar o mes do insight?
- Receber `category_limit` e `recurring_expense` para a mesma categoria no mesmo mes e repetitivo? Reavaliar com uso real.

## Task Breakdown Inicial

- [ ] Task: Escrever cenario realista e testes de service.
  - Acceptance: testes cobrem inclusao, exclusao, idempotencia e silenciamento.
  - Verify: `python manage.py test insights`.
  - Files: `insights/tests/scenarios.py`, `insights/tests/test_services.py`.
- [ ] Task: Implementar `generate_monthly_insights` e corrigir defeitos.
  - Acceptance: sem "None", media quantizada, mensagens em BRL, aprovacao sem `AttributeError`.
  - Verify: testes de service e de view.
  - Files: `insights/services.py`.
- [ ] Task: Criar o command `generate_insights`.
  - Acceptance: gera insights no banco local de forma idempotente.
  - Verify: `insights/tests/test_commands.py` e execucao manual.
  - Files: `insights/management/commands/generate_insights.py`.
