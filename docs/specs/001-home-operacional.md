# Spec 001 - Home Operacional

## Contexto

A home atual nao deve ser apenas uma colecao de atalhos. Ela precisa virar a primeira tela operacional do app, mostrando o estado do mes, pendencias e sugestoes acionaveis.

A previa `ui-preview-monarch-maybe-rocket.html` foi aprovada como referencia visual para essa direcao.

## Objetivo

Transformar `/` em uma home acionavel, util mesmo com poucos dados, separando claramente a visao do agora dos relatorios historicos.

## Fora de Escopo

- Substituir `/reports/month/`.
- Criar exportacao de relatorios.
- Implementar ML/LLM para sugestoes.
- Criar graficos complexos nesta primeira entrega.

## Estado Atual

A home funciona mais como ponto de entrada para outras telas. O app ja possui dados financeiros, cards, sidebar e alguns graficos em relatorios, mas a home ainda nao resume pendencias e decisoes do mes.

## Comportamento Esperado

A home deve responder:

- Como esta meu mes agora?
- O que exige minha atencao?
- Quais decisoes preciso tomar?
- Quais atalhos uso com frequencia?

Quando houver dados reais, eles devem alimentar a tela. Quando nao houver dados, os blocos devem mostrar estados vazios com chamadas para acao.

## Telas e Componentes

Telas afetadas:

- `/`;
- template `core/home.html`;
- possiveis partials de card, estado vazio, badge e lista curta.

Blocos esperados:

- resumo financeiro do mes;
- faturas proximas ou vencidas;
- importacoes pendentes;
- recorrencias previstas;
- metas em risco;
- insights pendentes;
- atalhos rapidos.

## Regras de Negocio

- Home usa dados reais quando existirem.
- Home nao marca recorrencia, fatura, insight ou importacao como resolvidos.
- Home nao deve criar lancamento pago automaticamente.
- Pendencias devem apontar para a tela responsavel pelo fluxo completo.
- Faturas vencidas e metas em risco devem ter prioridade visual maior.

## Dados, Services e Selectors

Criar ou evoluir:

- selector `get_operational_home_context`;
- selectors auxiliares para resumo mensal, faturas proximas, importacoes pendentes, insights pendentes e metas em risco;
- contexto pronto para o template, evitando regra de negocio complexa na view.

Contrato minimo do contexto:

```text
summary       -> resumo financeiro do mes atual
alerts        -> alertas priorizados da home
pending_items -> pendencias acionaveis
quick_actions -> atalhos rapidos fixos
empty_states  -> estados vazios com CTA
```

## Estados de Erro

- Banco vazio deve renderizar sem excecao.
- Falta de conta, cartao ou categoria deve gerar CTA, nao erro tecnico.
- Erros inesperados em bloco especifico nao devem impedir a home inteira de renderizar, quando for razoavel isolar o bloco.

## Testes Esperados

- Selector com banco vazio.
- Selector com transacoes reais.
- View `/` renderizando com banco vazio.
- View `/` renderizando pendencias.
- Links principais presentes.
- Nenhuma query ou regra financeira complexa no template.

## Criterios de Aceite

- `/` mostra overview financeiro.
- Home nao e apenas lista de botoes.
- Home mostra pendencias acionaveis.
- Home renderiza com banco vazio.
- Home nao substitui relatorios.
- Testes de view e selector passam.

## Issues Sugeridas

- Criar selector `get_operational_home_context`.
- Redesenhar `core/home.html`.
- Adicionar cards de resumo mensal.
- Adicionar bloco de faturas proximas.
- Adicionar bloco de importacoes pendentes.
- Adicionar bloco de insights pendentes.
- Adicionar estados vazios com CTA.
- Criar testes da home.

## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- A home usa Django template, sem SPA.
- A rota `/` continua no app `core`.
- Os dados devem vir de selectors, nao de regra no template.
- A previa `ui-preview-monarch-maybe-rocket.html` serve como referencia visual, nao como HTML final obrigatorio.

## Decisoes da Spec Review

- A home usa o mes atual como periodo padrao.
- Seletor de periodo fica fora do MVP da home operacional.
- Esta spec nao muda schema.
- O selector principal deve retornar, no minimo, as chaves `summary`, `alerts`, `pending_items`, `quick_actions` e `empty_states`.
- O resumo financeiro do mes separa valores realizados de valores previstos ou pendentes.
- Transferencias nao entram como receita ou despesa no resumo mensal.
- Faturas proximas sao faturas vencidas ou com vencimento em ate 15 dias.
- Metas em risco no MVP sao metas ou categorias ja ultrapassadas ou acima de 80% do limite, quando os dados existirem.
- Pendencias de importacao, insights, recorrencias, faturas e metas devem usar os modelos/status ja existentes; se algum dado ainda nao existir, o bloco deve retornar vazio ou estado vazio, nao criar regra nova.
- Isolamento avancado de erro por bloco fica fora da primeira issue; o MVP deve garantir banco vazio sem excecao.
- Prioridade inicial dos alertas:
  1. faturas vencidas ou proximas do vencimento;
  2. importacoes pendentes;
  3. metas ou categorias em risco.
- Atalhos rapidos serao fixos no MVP.

## Open Questions

- Nenhuma pergunta aberta bloqueante nesta spec.

## Task Breakdown Inicial

- [ ] Task: Criar selector da home operacional.
  - Acceptance: contexto da home retorna `summary`, `alerts`, `pending_items`, `quick_actions` e `empty_states` para o mes atual, sem alterar schema.
  - Verify: `python manage.py test core`.
  - Files: `core/selectors.py`, `core/tests/`.
- [ ] Task: Redesenhar template da home.
  - Acceptance: `/` mostra overview, alertas, sugestoes e atalhos.
  - Verify: view test e validacao manual desktop/mobile.
  - Files: `core/templates/core/home.html`, `static/css/app.css`.
- [ ] Task: Adicionar blocos de pendencias.
  - Acceptance: faturas, importacoes, insights e metas aparecem quando existirem.
  - Verify: testes de selector e view.
  - Files: `core/selectors.py`, `core/views.py`, `core/tests/`.
