# Spec 003 - Feedback, Validacoes e Confirmacoes

## Contexto

Alguns fluxos operacionais ainda retornam JSON puro ou comunicam erro/sucesso de forma pouco integrada a tela. Em um app financeiro, feedback claro reduz medo, erro e retrabalho.

## Objetivo

Padronizar fluxos web com `POST -> service -> messages -> redirect`, mantendo JSON apenas para endpoints intencionalmente API ou assincronos.

## Fora de Escopo

- Criar API publica.
- Reescrever todas as views do projeto de uma vez.
- Adotar framework frontend pesado.

## Estado Atual

O projeto possui services e views funcionais, mas ainda ha diferencas entre telas HTML, endpoints JSON, redirects, messages e tratamento de `ValidationError`.

## Comportamento Esperado

- Fluxos de tela usam messages e redirect.
- JSON fica restrito a endpoints planejados como API/async.
- Acoes financeiras sensiveis exibem impacto antes da confirmacao.
- Erros aparecem no formulario ou no contexto da acao.

## Telas e Componentes

Componentes envolvidos:

- partial de confirmacao;
- message boxes;
- forms com erros por campo;
- botoes de acao sensivel.

Acoes sensiveis iniciais:

- pagar fatura;
- fechar fatura;
- cancelar parcelamento;
- descartar importacao;
- confirmar importacoes em lote;
- aprovar insight;
- silenciar insight;
- criar transferencia;
- editar transacao paga.

## Regras de Negocio

- Services devem concentrar validacao de negocio.
- Views traduzem sucesso/erro para messages e redirects.
- Confirmacao de pagamento de fatura deve mostrar conta, saldo atual, valor e saldo projetado.
- Editar transacao paga deve deixar claro se saldo sera recalculado.

## Dados, Services e Selectors

Mapear:

- views com `JsonResponse`;
- services que podem levantar `ValidationError`;
- fluxos POST sem feedback visual suficiente;
- dados necessarios para confirmacoes contextuais.

## Estados de Erro

- `ValidationError` deve virar erro de form ou message de erro.
- Falhas em lote devem mostrar erros por item quando possivel.
- Confirmacao cancelada pelo usuario nao deve alterar dados.

## Testes Esperados

- POST com sucesso redireciona e cria message.
- POST invalido nao quebra tela.
- Acoes sensiveis exibem confirmacao.
- Endpoints JSON restantes sao intencionais e documentados.

## Criterios de Aceite

- Nenhum fluxo operacional retorna JSON cru sem intencao.
- Acoes financeiras mostram sucesso/erro claro.
- Validacoes aparecem no contexto correto.
- Testes cobrem redirects e messages.

## Issues Sugeridas

- Mapear views com `JsonResponse`.
- Converter fluxos de insights para HTML/messages quando aplicavel.
- Criar confirmacao para pagamento de fatura.
- Criar confirmacao para cancelamento de parcelamento.
- Criar padrao de erro de service para forms.
- Testar messages em POSTs principais.
## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- Fluxos HTML devem usar messages e redirect.
- JSON continua permitido apenas para endpoints API/async intencionais.
- Confirmacoes podem comecar simples e evoluir para modal/partial.
- Services continuam sendo a camada principal de validacao de negocio.

## Open Questions

- Confirmacoes sensiveis devem ser tela intermediaria, modal reutilizavel ou `confirm()` temporario?
- Quais endpoints JSON atuais sao APIs intencionais e quais sao fluxo web incompleto?
- Editar transacao paga deve recalcular saldo automaticamente ou exigir fluxo de reversao?

## Task Breakdown Inicial

- [ ] Task: Mapear todos os `JsonResponse`.
  - Acceptance: cada retorno JSON fica classificado como API/async ou fluxo web a converter.
  - Verify: lista revisada na issue.
  - Files: `*/views.py`, spec da issue.
- [ ] Task: Criar padrao de confirmacao para pagamento de fatura.
  - Acceptance: usuario ve conta, saldo, valor e saldo projetado antes de pagar.
  - Verify: testes de GET/POST e messages.
  - Files: `cards/views.py`, `cards/templates/`, `cards/tests/`.
- [ ] Task: Padronizar erro de service para forms/messages.
  - Acceptance: `ValidationError` aparece no contexto correto.
  - Verify: testes de POST invalido.
  - Files: views/forms dos fluxos escolhidos.
