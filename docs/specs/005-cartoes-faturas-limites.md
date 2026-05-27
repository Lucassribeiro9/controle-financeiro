# Spec 005 - Cartoes, Faturas e Limites

## Contexto

Cartoes e faturas sao parte central do uso diario. O usuario precisa entender limite usado, limite disponivel, vencimento, status da fatura e impacto do pagamento sem precisar navegar por caminhos indiretos.

## Objetivo

Melhorar dominio e UX de cartoes/faturas, consumir limite de credito ao lancar compra e dar acesso direto as faturas.

## Fora de Escopo

- Integracao bancaria automatica.
- Pagamento real via API bancaria.
- Controle multiusuario.
- Alterar retroativamente todas as faturas antigas sem migracao planejada.

## Estado Atual

O app ja possui cartoes, faturas e pagamentos, mas compras pendentes no credito ainda precisam consumir limite de forma clara. Faturas tambem precisam de acesso direto e visual mais dinamico.

## Comportamento Esperado

- Compra no credito reduz limite disponivel no momento do lancamento.
- Faturas aparecem em menu/rota propria.
- Fatura aberta mostra valor previsto.
- Fatura fechada mostra valor fechado.
- Fatura paga mostra valor pago e conta usada.
- Pagamento parcial altera indicadores de forma clara.

## Telas e Componentes

Telas afetadas:

- lista de cartoes;
- detalhe de cartao;
- lista de faturas;
- detalhe de fatura;
- pagamento de fatura;
- criacao de compra no credito.

Componentes:

- indicador de limite usado;
- indicador de limite disponivel;
- resumo de fatura;
- confirmacao de pagamento;
- badge de status.

## Regras de Negocio

- Limite disponivel deve ser calculado inicialmente, nao persistido.
- Limite usado considera compras `card_purchase` nao canceladas/ignoradas em faturas abertas ou pendentes.
- Compra pendente no credito consome limite.
- Cancelamento ou ignorar compra remove a compra do limite usado.
- Beneficio deve consumir saldo/limite conforme sua modalidade.
- Pagamento de fatura deve indicar conta de saida.

## Dados, Services e Selectors

Criar ou evoluir:

- selector de limite usado/disponivel;
- selector de resumo de fatura;
- service de pagamento com contexto de saldo projetado;
- rotas diretas para faturas.

## Estados de Erro

- Pagamento sem conta deve ser bloqueado.
- Pagamento maior que saldo deve avisar ou bloquear conforme regra definida.
- Compra que excede limite deve exibir alerta claro.
- Fatura inexistente ou ja paga deve ter feedback contextual.

## Testes Esperados

- Compra pendente consome limite.
- Compra cancelada nao consome limite.
- Fatura aberta calcula valor previsto.
- Fatura fechada calcula valor fechado.
- Pagamento parcial atualiza indicadores.
- Pagamento de fatura cria impacto na conta correta.

## Criterios de Aceite

- Compra no credito reduz limite disponivel.
- Cancelamento/ignorar remove compra do limite.
- Fatura fica acessivel sem entrar em Cartoes.
- Usuario entende o que esta aberto, fechado, pago e pendente.

## Issues Sugeridas

- Criar selector de limite usado/disponivel.
- Mostrar limite em lista de cartoes.
- Criar rota/menu direto para faturas.
- Melhorar detalhe de fatura.
- Adicionar confirmacao contextual de pagamento.
- Integrar parcelamentos na fatura.
- Testar limite consumido por compra pendente.
## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- Limite disponivel sera calculado, nao persistido inicialmente.
- Compra pendente no credito consome limite.
- Faturas devem ter rota/menu direto.
- Pagamento de fatura precisa indicar conta de saida.

## Open Questions

- Limite usado considera apenas fatura atual/aberta ou tambem compras futuras parceladas?
- Compra que excede limite deve bloquear ou apenas alertar no MVP?
- Como beneficios com saldos separados, como alimentacao e transporte, entram no calculo?
- Pagamento parcial deve permitir varios pagamentos por fatura ou atualizar um campo acumulado?

## Task Breakdown Inicial

- [ ] Task: Criar selector de limite usado/disponivel.
  - Acceptance: compras pendentes e abertas reduzem limite disponivel.
  - Verify: testes de selector.
  - Files: `cards/selectors.py`, `cards/tests/`.
- [ ] Task: Criar acesso direto a faturas.
  - Acceptance: menu/rota permite acessar faturas sem entrar em cartoes.
  - Verify: teste de navegacao e view.
  - Files: `cards/urls.py`, `cards/views.py`, `templates/partials/nav_links.html`.
- [ ] Task: Melhorar detalhe de fatura.
  - Acceptance: tela mostra vencimento, status, previsto, fechado, pago e conta de pagamento.
  - Verify: teste de view e validacao manual.
  - Files: `cards/templates/cards/statement_detail.html`, `cards/tests/`.
