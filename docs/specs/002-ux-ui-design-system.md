# Spec 002 - UX/UI Design System

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

## Decisoes da Spec Review

- O projeto adotara `lucide icons` quando a integracao encaixar bem com Django templates.
- Tema escuro fica fora do roadmap atual.
- A primeira tela piloto do design system sera a Home Operacional.

## Open Questions

- Nenhuma pergunta aberta bloqueante nesta spec.

## Task Breakdown Inicial

- [ ] Task: Criar baseline visual documentada.
  - Acceptance: cores, badges, cards, tabelas e filtros ficam documentados.
  - Verify: revisao manual da spec.
  - Files: `docs/specs/002-ux-ui-design-system.md`.
- [ ] Task: Criar partials essenciais.
  - Acceptance: `empty_state`, `status_badge` e `filter_bar` existem e sao reutilizaveis.
  - Verify: testes/smoke tests das telas piloto.
  - Files: `templates/partials/`, `core/tests/`.
- [ ] Task: Aplicar padrao em uma tela piloto.
  - Acceptance: tela piloto usa partials e mantem responsividade.
  - Verify: `python manage.py test` e validacao manual desktop/mobile.
  - Files: template da tela piloto, `static/css/app.css`.
