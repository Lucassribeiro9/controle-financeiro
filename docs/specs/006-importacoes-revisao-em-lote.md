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
- Aplicar tipo em lote para tipos alem de receita e despesa nesta fase.

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
- Alteracao em lote pode sobrescrever campos ja preenchidos quando o usuario executar explicitamente a acao em lote.
- Acao em lote para tipo deve permitir apenas `income` e `expense` nesta fase.
- Confirmacao parcial deve criar transacoes validas e manter itens invalidos pendentes para revisao.
- Erro em uma linha nao deve esconder o status das demais.
- Duplicidade deve ser tratada como alerta de revisao, nao como confirmacao, descarte ou bloqueio automatico.

## Dados, Services e Selectors

Criar ou evoluir:

- services de bulk action;
- selectors filtrados para revisao;
- parser XLSX respeitando celulas vazias;
- estrutura persistida no banco para erros por linha;
- identificacao de possiveis duplicidades por `date + amount + description normalizada + account`.

## Estados de Erro

- Arquivo invalido deve ter message clara.
- Linha invalida deve mostrar erro especifico.
- Nenhum item selecionado deve mostrar aviso.
- Acao em lote parcial deve informar o que foi aplicado e o que falhou.
- Item invalido em confirmacao parcial deve permanecer pendente com erro persistido.

## Testes Esperados

- Filtros de importacao.
- Acao em lote para conta.
- Acao em lote para categoria.
- Acao em lote para tipo limitada a `income` e `expense`.
- Confirmacao parcial.
- Parser XLSX com celulas vazias.
- Duplicidade identificada.
- Persistencia de erro por linha.

## Criterios de Aceite

- Usuario revisa importacoes em menos cliques.
- Conta/categoria podem ser aplicadas em lote.
- Tipo pode ser aplicado em lote apenas como receita ou despesa.
- Duplicadas ficam claras.
- Erros nao quebram lote inteiro sem explicacao.
- Confirmacao parcial cria transacoes validas e mantem invalidas pendentes.
- Erros por linha permanecem disponiveis ao sair e voltar para a revisao.

## Decisoes Fechadas

- Acoes em lote podem sobrescrever campos ja preenchidos quando o usuario selecionar itens e executar a acao explicitamente.
- Confirmacao parcial deve criar transacoes validas e manter itens invalidos pendentes.
- Erros por linha devem ser persistidos no banco.
- Acao em lote para tipo deve permitir apenas `income` e `expense` nesta fase.
- Possiveis duplicidades devem ser identificadas por `date + amount + description normalizada + account`.
- Possiveis duplicidades devem ser exibidas para revisao, sem descarte automatico.

## Backlog

- Avaliar se a revisao precisa de paginacao antes de novas acoes em lote.
- Avaliar filtros persistidos por query string, sessao ou ambos.
- Preparar campo de origem/confianca para sugestoes futuras com ML/LLM.
- Permitir ignorar duplicidades em lote apos a deteccao estar estabilizada.
- Avaliar processamento assincrono para arquivos grandes em spec futura.

## Issues Sugeridas

- `fix(imports): preservar celulas vazias no parser XLSX`.
- `feat(imports): persistir erros por linha na revisao`.
- `feat(imports): filtrar itens de revisao por status e periodo`.
- `feat(imports): filtrar itens de revisao por conta categoria tipo e texto`.
- `feat(imports): aplicar categoria em lote aos itens selecionados`.
- `feat(imports): aplicar conta em lote aos itens selecionados`.
- `feat(imports): aplicar tipo em lote como receita ou despesa`.
- `feat(imports): confirmar parcialmente itens validos do lote`.
- `feat(imports): destacar possiveis duplicidades na revisao`.
- `feat(imports): paginar revisao de importacao`.

## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- Importacoes continuam exigindo revisao antes de confirmar.
- Sugestoes automaticas futuras nao confirmam lancamentos sozinhas.
- Acoes em lote devem operar sobre selecao explicita.
- O importador XLSX precisa preservar celulas vazias.
- Acoes em lote executadas pelo usuario sao confirmacao suficiente para sobrescrever campos selecionados.

## Open Questions

- Nenhuma pergunta bloqueante no momento.
- A prioridade da paginacao fica em backlog e deve ser reavaliada conforme volume real de itens por lote.

## Task Breakdown Inicial

- [ ] Task: Corrigir parser XLSX para celulas vazias.
  - Acceptance: colunas nao sao deslocadas quando uma celula vem vazia.
  - Verify: teste de importador com arquivo/caso sintetico.
  - Files: `imports/importers.py`, `imports/tests/test_importers.py`.
- [ ] Task: Persistir erros por linha na revisao.
  - Acceptance: erro especifico do item permanece salvo e visivel ao reabrir a revisao.
  - Verify: teste de model/service para erro por item.
  - Files: `imports/models.py`, `imports/services.py`, `imports/tests/`.
- [ ] Task: Adicionar acao em lote para categoria.
  - Acceptance: usuario aplica categoria aos itens selecionados.
  - Verify: teste de service/view.
  - Files: `imports/services.py`, `imports/views.py`, `imports/tests/`.
- [ ] Task: Adicionar acao em lote para conta.
  - Acceptance: usuario aplica conta aos itens selecionados.
  - Verify: teste de service/view.
  - Files: `imports/services.py`, `imports/views.py`, `imports/tests/`.
- [ ] Task: Adicionar acao em lote para tipo.
  - Acceptance: usuario aplica apenas `income` ou `expense` aos itens selecionados.
  - Verify: teste de service/view cobrindo tipo invalido.
  - Files: `imports/services.py`, `imports/views.py`, `imports/tests/`.
- [ ] Task: Confirmar parcialmente itens validos.
  - Acceptance: itens validos criam transacoes e invalidos permanecem pendentes com erro.
  - Verify: teste de service/view para sucesso parcial.
  - Files: `imports/services.py`, `imports/views.py`, `imports/tests/`.
- [ ] Task: Destacar possiveis duplicidades.
  - Acceptance: itens com `date + amount + description normalizada + account` iguais aparecem como possivel duplicidade.
  - Verify: teste de selector/service de duplicidade.
  - Files: `imports/selectors.py`, `imports/services.py`, `imports/tests/`.
