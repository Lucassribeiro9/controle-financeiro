# Spec 002 - UX/UI Design System

> **Identidade visual e tema:** regidos pela ADR-007 (Wise no claro, escuro inspirado na Mercury), que substitui as referências visuais desta spec e o item "tema claro/escuro" de Fora de Escopo. Esta spec continua valendo para padrões de uso: filtros, badges, estados vazios e confirmações.
> ADR-007: https://lucasdevlop94-1792776715909.atlassian.net/wiki/spaces/FIN/pages/851969

## Contexto

O app ja tem uma base visual boa, com sidebar, icones, cards, tabelas e Chart.js. A proxima fase precisa formalizar esses padroes para evitar que cada tela evolua com solucoes diferentes.

## Objetivo

Criar uma linguagem visual consistente, natural e operacional, baseada em Monarch, Maybe, Rocket Money e inspiracao estetica pontual do Dribbble.

## Fora de Escopo

- Criar biblioteca de componentes frontend separada.
- Migrar para SPA.
- Recriar toda a identidade visual de uma vez.
- Implementar tema claro/escuro nesta spec.

## Estado Atual

Ha componentes e padroes espalhados em templates e CSS. Algumas telas ja estao bem organizadas, mas faltam contratos claros para filtros, badges, estados vazios, cards, tabelas e confirmacoes.

## Comportamento Esperado

As telas principais devem seguir padroes previsiveis:

- listas financeiras densas usam tabela ou lista compacta;
- resumo e dashboard usam cards;
- filtros ficam no topo, com limpar filtros;
- estados vazios mostram proxima acao;
- badges usam cores semanticas consistentes;
- mobile troca tabelas espremidas por blocos compactos quando necessario.

## Telas e Componentes

Partials recomendados:

```text
templates/partials/empty_state.html
templates/partials/filter_bar.html
templates/partials/confirm_action.html
templates/partials/period_selector.html
templates/partials/status_badge.html
templates/partials/action_row.html
```

Telas piloto:

- transacoes;
- faturas;
- importacoes;
- home.

## Regras de Negocio

- Verde representa pago, concluido ou saudavel.
- Amarelo representa pendente, atencao ou parcial.
- Azul representa previsto, informativo ou aberto.
- Vermelho representa atrasado, erro ou risco.
- Cinza representa cancelado, ignorado ou inativo.
- Cards nao devem substituir tabelas em listas financeiras densas.
- Percentual inteiro deve aparecer sem decimal.
- Mes deve aparecer de forma legivel, por exemplo `Maio/2026`.

## Dados, Services e Selectors

Esta spec nao deve criar regra financeira nova. Ela pode exigir ajustes de contexto para padronizar exibicao de:

- status;
- valores monetarios;
- porcentagens;
- periodo selecionado;
- estados vazios.

## Estados de Erro

- Formularios devem exibir erros no campo ou em message box proxima ao contexto.
- Estados vazios nao devem parecer erro.
- Filtros sem resultado devem permitir limpar filtros facilmente.

## Testes Esperados

- Smoke tests das views afetadas.
- Testes de template quando houver partials com logica condicional relevante.
- Testes para helpers de formatacao, caso sejam criados.

## Criterios de Aceite

- Telas principais usam padroes consistentes.
- Estados vazios tem acao util.
- Status tem cores previsiveis.
- Layout continua responsivo.
- Componentes parciais reduzem duplicacao.
- `docs/design/tokens.md` e referencia visual existem no repositorio.
- Partials MVP usados em pelo menos duas telas cada (quando aplicavel).
- Home, transacoes, faturas e importacoes seguem como telas piloto.
- Breakpoint 768px e lista empilhada abaixo disso (ADR-014), sem scroll horizontal.

## Open Questions

- Nenhuma pergunta aberta bloqueante nesta spec (decisoes registradas em **Decisoes da Spec Review**).

## Issues Sugeridas

- Documentar tokens visuais.
- Criar partial de estado vazio.
- Criar partial de badge/status.
- Criar partial de filtros.
- Padronizar filtros em uma tela piloto.
- Aplicar padrao em transacoes.
- Aplicar padrao em faturas.
- Aplicar padrao em importacoes.

## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- O projeto continua com Django templates e CSS proprio.
- Chart.js continua sendo a biblioteca de graficos.
- A UI deve ser operacional, sem visual artificial de IA.
- Componentes compartilhados ficam em `templates/partials/`.
- A Spec `001` precede funcionalmente a refatoração visual da home nesta spec.
- Ícones Lucide não fazem parte do MVP desta entrega.

## Decisões da Spec Review

### Ordem e dependência

- A Spec `001-home-operacional` deve estar funcionalmente estável antes da onda de partials e refatoração visual da home.
- A Spec `002` entrega em **3 ondas**: (1) documentação de tokens + partials essenciais, (2) home como tela piloto do design system, (3) transações, faturas e importações.
- A home já implementada na `001` será **refatorada** para usar partials da `002`; não se recria a camada de dados da home nesta spec.

### Referência visual

- A referência visual é `docs/design/DESIGN.md` e os PNGs do Figma em `docs/design/figma/` (spec 017); a prévia estática `ui-preview-home.html` foi removida na 3.1.
- Tokens e componentes ficam em `docs/design/DESIGN.md`; `docs/design/tokens.md` guarda a tabela status → variante.

### Escopo MVP de partials

- **MVP desta spec:** `empty_state`, `status_badge`, `filter_bar`.
- **Fora do MVP 002:** `confirm_action` → Spec `003-feedback-validacoes-confirmacoes`; `period_selector` → apenas quando uma issue de tela exigir; `action_row` → backlog.
- `filter_bar` no MVP é **markup + limpar filtros**, sem HTMX/JS adicional.

### Formatação e exibição

- Percentual **inteiro sem decimal** aplica-se a participação/share na UI (ex.: “32% das despesas”, metas em donut).
- Taxas e valores que exigem precisão (ex.: CDI) podem manter decimais via filtro `percentage` existente ou variante documentada.
- Período em títulos de seção usa formato legível (`Maio/2026`) via `month_name` + ano; formato numérico compacto (`5/2026`) fica restrito a filtros/controles compactos.

### Semântica de cores e badges

- A tabela de cores da spec **documenta e formaliza** o comportamento atual; mudanças em `STATUS_BADGE_VARIANTS` só entram quando explicitamente registradas em `docs/design/tokens.md`.
- O partial `status_badge` **reutiliza** o filtro `status_badge_class` em `core/templatetags/money.py`; não duplica mapa de status no template.
- Status financeiros e status de metas compartilham quatro variantes do DESIGN.md: `positive`, `warning`, `neutral` e `negative` (classes `status status--<variante>`). Atualizado na 3.1 (spec 017, D6): `info` e `neutral` viram Neutro, então previsto, aberto e `on_track` deixam de ser azul. `active_badge_class` segue a mesma regra (`positive` ou `neutral`).

### Mobile e responsividade

- Breakpoint oficial: **768px**.
- A partir da 3.1 (spec 017): `filter_bar` aceita `fields_template`, `active_count` e `clear_url` e vira `<details class="filters">`, recolhido abaixo de 768px com o resumo "Filtros (N ativos)" e aberto acima disso, sem JS. Sem `fields_template` renderiza só as ações. Listas viram lista empilhada abaixo de 768px (ADR-014) nas issues de tela.
- **Lista empilhada (ADR-014):** abaixo de 768px toda lista financeira vira linhas empilhadas (`.list-table`, com `.list-table--records` nos cadastros), sem scroll horizontal. Substitui o MVP de scroll horizontal e a onda 2 de cards empilhados, entregues na remodelação (spec 017).

### Componentes compartilhados (`static/css/components.css`)

- Regra (spec 017, 3.9): `static/css/app.css` não existe mais. Qualquer issue pode criar ou alterar um componente em `components.css`, com teste e entrada nesta lista. Promova um padrão quando ele se repetir em dois apps. `static/css/pages/<app>.css` guarda só o que é local do app (prefixo próprio). `base.html` carrega `tokens.css`, `base.css`, `components.css`, `layout.css` e o bloco `page_css`.
- Base: `.btn` (`--primary`, `--secondary`, `--tertiary`, `--danger`), `.status`, `.card`, `.balance-card`, `.field` (`--check`), `.alert`, `.segmented`, `.period-picker`, `.filters`, `.list-table`, `.summary-rows`, `.progress` (barra lima; `--over` vermelha), `.empty`.
- Cadastros (accounts, categories, institutions, installments, login): `.screen-head` (com `__title` e `__actions`), `.soft-text`, `.card-stack`, `.card-head`, `.card-section`, `.form-card`, `.form-stack`, `.button-bar`, `.list-card`, `.row-main`, `.row-meta`, `.row-value` e o modificador `.list-table--records` (linha empilhada abaixo de 768px, nome e valor na primeira linha, metadados na segunda).
- Utilitários: `.sr-only` (texto só para leitor de tela) e `.app-messages` (pilha das mensagens do Django, `partials/messages.html`).

### Ícones

- **Lucide** fica **fora do MVP** desta spec; a sidebar e navegação mantêm SVG inline até issue dedicada.

### Testes e critérios de aceite

- Cada partial do MVP deve ter **pelo menos um teste de template** (classes, CTA, variantes).
- Telas piloto: smoke das views + validação manual desktop/mobile conforme `docs/specs/000-sdd-baseline.md`.
- Critério “reduz duplicação”: cada partial do MVP usado em **no mínimo duas telas** (ex.: `empty_state` na home e em uma lista piloto).

### Relação com outras specs

- Spec `003`: confirmações, messages e `confirm_action`.
- Spec `001`: home operacional é a primeira tela piloto visual após partials.

### Partials no MVP vs. backlog

| Partial | MVP 002 | Observação |
| --- | --- | --- |
| `empty_state.html` | Sim | CTA obrigatório; não usar estilo de erro |
| `status_badge.html` | Sim | Envolve `status_badge_class` |
| `filter_bar.html` | Sim | Limpar filtros; sem HTMX no MVP |
| `confirm_action.html` | Não | Spec 003 |
| `period_selector.html` | Não | Sob demanda por tela |
| `action_row.html` | Não | Backlog |

### Artefatos de design

- `docs/design/DESIGN.md` — tokens, tipografia e componentes (referência visual aprovada).
- `docs/design/tokens.md` — semântica de status e variantes.

## Task Breakdown Inicial

- [ ] Issue 002-01: Documentar baseline visual e tokens.
  - Acceptance: `docs/design/tokens.md` + referência visual em `docs/design/`; tabela status → variante alinhada a `STATUS_BADGE_VARIANTS`.
  - Verify: revisão humana; link nesta spec.
  - Files: `docs/design/tokens.md`, `docs/design/DESIGN.md`, `docs/specs/002-ux-ui-design-system.md`.

- [ ] Issue 002-02: Criar partial `status_badge`.
  - Acceptance: partial reutilizável; usa `status_badge_class`; adotado na home e em pelo menos uma lista.
  - Verify: `python manage.py test core transactions` (ou app da lista escolhida); teste de template do partial.
  - Files: `templates/partials/status_badge.html`, templates piloto, `core/tests/`.

- [ ] Issue 002-03: Criar partial `empty_state`.
  - Acceptance: contrato `title`, descrição, `cta_label`, `cta_url`; home deixa markup ad hoc onde couber.
  - Verify: `python manage.py test core`; validação manual home vazia/com dados.
  - Files: `templates/partials/empty_state.html`, `core/templates/core/home.html`, `core/tests/`.

- [ ] Issue 002-04: Criar partial `filter_bar`.
  - Acceptance: campos configuráveis + “Limpar filtros”; sem resultado ≠ erro.
  - Verify: teste de template; smoke em transações.
  - Files: `templates/partials/filter_bar.html`, `transactions/templates/`, `transactions/tests/`.

- [ ] Issue 002-05: Padronizar percentual inteiro e período legível.
  - Acceptance: filtro/convenção para % inteiro em shares; `month_name` em títulos piloto documentado.
  - Verify: `python manage.py test core`.
  - Files: `core/templatetags/money.py`, `core/tests/test_formatting.py`, `docs/design/tokens.md`.

- [ ] Issue 002-06: Aplicar design system na home (piloto).
  - Acceptance: home usa partials do MVP; responsivo em 768px; sem regra financeira no template.
  - Verify: `python manage.py test core`; validação manual desktop/mobile.
  - Files: `core/templates/core/home.html`, `static/css/pages/home.css`.

- [ ] Issue 002-07: Padronizar lista de transações.
  - Acceptance: `filter_bar`, `status_badge`, `empty_state`; lista empilhada abaixo de 768px (ADR-014).
  - Verify: `python manage.py test transactions`; manual mobile.
  - Files: `transactions/templates/transactions/list.html`, `static/css/pages/transactions.css`.

- [ ] Issue 002-08: Padronizar faturas (lista/detalhe relevante).
  - Acceptance: partials do MVP nas telas de faturas piloto.
  - Verify: `python manage.py test cards`.
  - Files: `cards/templates/cards/`.

- [ ] Issue 002-09: Padronizar revisão de importações.
  - Acceptance: badges e empty/filter alinhados; sem alterar regras de staging/confirmação.
  - Verify: `python manage.py test imports`.
  - Files: `imports/templates/imports/review.html`.

- [ ] Issue 002-10 (backlog / onda 2): Consolidar tokens em variáveis CSS e cards empilhados em transações/faturas.
  - Acceptance: `--color-*` semânticos; cards mobile onde aplicável.
  - Verify: `python manage.py test`; revisão visual nas telas piloto.
  - Files: `static/css/tokens.css`, `static/css/components.css`, `docs/design/tokens.md`.