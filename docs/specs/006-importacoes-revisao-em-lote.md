# Spec 006 - Importacoes e Revisao em Lote

## Contexto

Importacoes sao uma ponte importante entre planilhas, OFX e o app. A revisao precisa ser rapida, clara e segura, principalmente quando houver muitos registros.

## Objetivo

Tornar importacoes mais rapidas de revisar e preparar o terreno para sugestoes futuras com ML/LLM, sem depender delas agora.

## Fora de Escopo

- Implementar ML/LLM.
- Confirmar lancamentos automaticamente sem revisao.
- Criar importacao bancaria via API.
- Processar arquivos muito grandes de forma assincrona nesta spec.

## Estado Atual

O importador ja existe e os filtros melhoraram, mas ainda podem ficar mais dinamicos. Acoes em lote precisam permitir alteracao de conta, categoria e tipo.

## Comportamento Esperado

- Usuario filtra importacoes por status, periodo, conta, categoria, tipo e texto quando aplicavel.
- Usuario seleciona itens explicitamente para acoes em lote.
- Usuario pode aplicar conta, categoria e tipo em lote.
- Erros por linha aparecem sem apagar todo o trabalho de revisao.
- Duplicadas ficam claras.

## Telas e Componentes

Telas afetadas:

- upload de importacao;
- lista de lotes;
- revisao de importacao;
- confirmacao em lote.

Componentes:

- filtros persistentes;
- selecao em lote;
- acoes em lote;
- mensagens por linha;
- paginacao.

## Regras de Negocio

- Confirmar lote exige selecao explicita.
- Sugestao automatica futura sempre deve ser revisavel.
- Alteracao em lote nao deve sobrescrever campo alterado manualmente sem confirmacao clara, se essa regra for adotada.
- Erro em uma linha nao deve esconder o status das demais.

## Dados, Services e Selectors

Criar ou evoluir:

- services de bulk action;
- selectors filtrados para revisao;
- parser XLSX respeitando celulas vazias;
- estrutura para erros por linha.

## Estados de Erro

- Arquivo invalido deve ter message clara.
- Linha invalida deve mostrar erro especifico.
- Nenhum item selecionado deve mostrar aviso.
- Acao em lote parcial deve informar o que foi aplicado e o que falhou.

## Testes Esperados

- Filtros de importacao.
- Acao em lote para conta.
- Acao em lote para categoria.
- Acao em lote para tipo.
- Confirmacao parcial.
- Parser XLSX com celulas vazias.
- Duplicidade identificada.

## Criterios de Aceite

- Usuario revisa importacoes em menos cliques.
- Conta/categoria podem ser aplicadas em lote.
- Duplicadas ficam claras.
- Erros nao quebram lote inteiro sem explicacao.

## Issues Sugeridas

- Melhorar filtros de importacoes.
- Adicionar acao em lote para conta.
- Adicionar acao em lote para categoria.
- Adicionar acao em lote para tipo.
- Melhorar mensagens de erro por linha.
- Adicionar paginacao.
- Testar confirmacao parcial.
## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- Importacoes continuam exigindo revisao antes de confirmar.
- Sugestoes automaticas futuras nao confirmam lancamentos sozinhas.
- Acoes em lote devem operar sobre selecao explicita.
- O importador XLSX precisa preservar celulas vazias.

## Open Questions

- Alteracao em lote deve sobrescrever campos ja alterados manualmente?
- A revisao precisa de paginacao antes ou depois das acoes em lote?
- Erros por linha devem ficar persistidos no banco ou apenas na sessao/tela?
- Confirmacao parcial deve criar transacoes validas e manter invalidas pendentes?

## Task Breakdown Inicial

- [ ] Task: Corrigir parser XLSX para celulas vazias.
  - Acceptance: colunas nao sao deslocadas quando uma celula vem vazia.
  - Verify: teste de importador com arquivo/caso sintetico.
  - Files: `imports/importers.py`, `imports/tests/test_importers.py`.
- [ ] Task: Adicionar acao em lote para categoria.
  - Acceptance: usuario aplica categoria aos itens selecionados.
  - Verify: teste de service/view.
  - Files: `imports/services.py`, `imports/views.py`, `imports/tests/`.
- [ ] Task: Adicionar acao em lote para conta.
  - Acceptance: usuario aplica conta aos itens selecionados.
  - Verify: teste de service/view.
  - Files: `imports/services.py`, `imports/views.py`, `imports/tests/`.
