# Spec 007 - Categorias, Metas e Limites

## Contexto

Categorias precisam ajudar o usuario a entender e decidir, nao apenas classificar dados. Limites por categoria podem se conectar naturalmente com metas mensais de reducao.

## Objetivo

Tornar categorias mais uteis para o usuario final e conectar categorias a limites, metas mensais e alertas.

## Fora de Escopo

- Classificacao automatica com ML/LLM.
- Reestruturar todo o app de goals.
- Criar sistema complexo de budgets antes de validar UX.

## Estado Atual

Categorias existem como apoio a classificacao. A tela ainda pode ser mais atrativa e mais orientada a decisao.

## Comportamento Esperado

- Categoria pode ter icone e cor opcionais.
- Categoria pode gerar limite mensal.
- Limite mensal deve ser representado como meta mensal de reducao quando fizer sentido.
- Categoria mostra gasto atual do mes, limite/meta e tendencia.
- Limites relevantes aparecem na home/dashboard.

## Telas e Componentes

Telas afetadas:

- lista de categorias;
- criacao/edicao de categoria;
- objetivos/metas mensais;
- home;
- dashboard.

Componentes:

- icone de categoria;
- badge de tendencia;
- indicador de uso do limite;
- CTA para criar meta mensal.

## Regras de Negocio

- Icone e cor sao opcionais.
- Limite mensal nao deve impedir lancamento por padrao; ele deve alertar.
- Categoria pode virar meta mensal de reducao.
- Subcategoria nao herda limite automaticamente sem decisao explicita.
- Limite excedido pode gerar insight.

## Dados, Services e Selectors

Criar ou evoluir:

- campos opcionais de icone/cor, se aprovados na issue;
- service para criar meta mensal a partir de categoria;
- selector de gasto mensal por categoria;
- selector de categorias em risco.

## Estados de Erro

- Limite negativo deve ser invalido.
- Icone invalido deve cair para valor padrao ou erro de form.
- Categoria sem dados deve mostrar estado vazio util.

## Testes Esperados

- Criar categoria com icone/cor.
- Criar limite mensal.
- Gerar meta mensal de reducao.
- Calcular gasto atual da categoria.
- Exibir categoria em risco na home/dashboard.

## Criterios de Aceite

- Tela de categorias ajuda decisao, nao so cadastro.
- Categoria pode virar meta mensal.
- Limite aparece em home/dashboard quando relevante.
- Estrutura continua preparada para ML/LLM futuro.

## Issues Sugeridas

- Adicionar icone/cor opcional na categoria.
- Melhorar tela de categorias.
- Criar fluxo "criar limite mensal".
- Integrar limite com `MonthlyGoal`.
- Mostrar limite no dashboard/home.
- Testar criacao de meta por categoria.
## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- Categorias continuam sendo app proprio.
- Icone e cor sao opcionais.
- Limite mensal deve se conectar a metas mensais, nao bloquear lancamentos.
- ML/LLM fica fora desta fase.

## Open Questions

- Icones serao nomes de uma biblioteca, emoji, classe CSS ou valor livre validado?
- Cor sera paleta fechada ou input livre?
- Limite mensal deve morar em `Category`, em `MonthlyGoal` ou em uma entidade de budget?
- Subcategorias entram no limite da categoria pai?

## Task Breakdown Inicial

- [ ] Task: Definir representacao de icone/cor.
  - Acceptance: decisao documentada antes de migration.
  - Verify: revisao da issue.
  - Files: `docs/specs/007-categorias-metas-limites.md`.
- [ ] Task: Melhorar tela de categorias com dados do mes.
  - Acceptance: categoria mostra gasto atual, tendencia e CTA de limite/meta.
  - Verify: testes de selector/view.
  - Files: `categories/selectors.py`, `categories/templates/`, `categories/tests/`.
- [ ] Task: Criar fluxo para meta mensal por categoria.
  - Acceptance: usuario cria meta de reducao a partir de uma categoria.
  - Verify: testes de service/view.
  - Files: `goals/services.py`, `categories/views.py`, `goals/tests/`.
