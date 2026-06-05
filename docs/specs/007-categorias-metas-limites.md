# Spec 007 - Categorias, Metas e Limites

## Contexto

Categorias precisam ajudar o usuario a entender e decidir, nao apenas classificar dados. Limites por categoria podem se conectar naturalmente com metas mensais de reducao.

## Objetivo

Tornar categorias mais uteis para o usuario final e conectar categorias a limites, metas mensais e alertas.

## Fora de Escopo

- Classificacao automatica com ML/LLM.
- Reestruturar todo o app de goals.
- Criar sistema complexo de budgets antes de validar UX.
- Usar emoji como icone de categoria nesta fase.

## Estado Atual

Categorias existem como apoio a classificacao. A tela ainda pode ser mais atrativa e mais orientada a decisao.

## Comportamento Esperado

- Categoria pode ter icone e cor opcionais.
- Icone deve ser escolhido por nome validado de uma biblioteca/conjunto de icones alinhado ao visual dos menus.
- Cor deve usar preset/paleta fechada.
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
- Icone deve ser nome validado de icone, nao emoji nem valor livre sem validacao.
- Cor deve ser um preset validado, nao input livre.
- Limite mensal nao deve impedir lancamento por padrao; ele deve alertar.
- Categoria pode virar meta mensal de reducao usando `Goal`/`MonthlyGoal`.
- Subcategoria nao herda limite automaticamente sem decisao explicita.
- Tendencia deve ser calculada inicialmente pelo percentual de uso do limite: ok, em risco e excedido.
- Limite excedido pode gerar insight.

## Dados, Services e Selectors

Criar ou evoluir:

- campos opcionais de icone/cor em `Category`;
- service para criar meta mensal de reducao a partir de categoria usando `Goal` e `MonthlyGoal`;
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

## Decisoes Fechadas

- Limite mensal de categoria deve ser representado por `Goal` de reducao com `MonthlyGoal`, sem criar entidade nova de budget nesta fase.
- `Category` pode receber campos opcionais de apresentacao: `icon` e `color`.
- Icones devem ser nomes validados de uma biblioteca/conjunto de icones alinhado aos icones dos menus.
- Emojis nao devem ser usados como icones de categoria nesta fase.
- Cores devem vir de preset/paleta fechada, nao de input livre.
- Subcategorias nao entram automaticamente no limite da categoria pai.
- Tendencia inicial deve ser baseada no percentual de uso do limite:
  - abaixo de 80%: ok;
  - de 80% ate abaixo de 100%: em risco;
  - maior ou igual a 100%: excedido.
- Limite mensal deve alertar e orientar decisao, nunca bloquear lancamento por padrao.

## Backlog

- Permitir limite recorrente automatico para meses futuros.
- Avaliar multiplos limites por categoria e periodo.
- Permitir inclusao explicita de subcategorias no limite da categoria pai.
- Gerar insight automaticamente quando limite for excedido.
- Criar picker visual de icones.
- Mostrar grafico de tendencia com Chart.js no dashboard quando o dado ajudar a decisao.

## Issues Sugeridas

- `docs(spec): fechar decisoes da spec 007`.
- `feat(categories): adicionar icone e cor opcionais`.
- `feat(categories): mostrar gasto mensal na lista`.
- `feat(goals): criar meta mensal de reducao por categoria`.
- `feat(categories): exibir status de limite por categoria`.
- `feat(dashboard): mostrar categorias em risco`.

## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- Categorias continuam sendo app proprio.
- Icone e cor sao opcionais.
- Limite mensal deve se conectar a metas mensais, nao bloquear lancamentos.
- ML/LLM fica fora desta fase.

## Open Questions

- Nenhuma pergunta bloqueante no momento.
- Decisoes futuras sobre recorrencia automatica, multiplos limites, subcategorias inclusas explicitamente, insights automaticos, picker visual e graficos ficam em backlog.

## Task Breakdown Inicial

- [ ] Task: Adicionar icone/cor opcionais em categoria.
  - Acceptance: `Category` aceita icone validado e cor de preset, ambos opcionais, sem emoji.
  - Verify: testes de model/form/view.
  - Files: `categories/models.py`, `categories/forms.py`, `categories/tests/`.
- [ ] Task: Documentar decisoes fechadas da spec.
  - Acceptance: spec registra decisoes de icone, cor, limite, subcategoria e tendencia.
  - Verify: revisao da spec.
  - Files: `docs/specs/007-categorias-metas-limites.md`.
- [ ] Task: Melhorar tela de categorias com dados do mes.
  - Acceptance: categoria mostra gasto atual, tendencia e CTA de limite/meta.
  - Verify: testes de selector/view.
  - Files: `categories/selectors.py`, `categories/templates/`, `categories/tests/`.
- [ ] Task: Criar fluxo para meta mensal por categoria.
  - Acceptance: usuario cria meta de reducao a partir de uma categoria.
  - Verify: testes de service/view.
  - Files: `goals/services.py`, `categories/views.py`, `goals/tests/`.
