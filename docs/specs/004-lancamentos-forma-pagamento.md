# Spec 004 - Lancamentos e Forma de Pagamento

## Contexto

O modelo interno do app separa transacoes, cartoes, faturas, beneficios, transferencias e parcelamentos. Para o usuario, porem, registrar um gasto deve parecer mais natural: escolher forma de pagamento e preencher apenas o que faz sentido.

## Objetivo

Criar um fluxo de lancamento orientado por forma de pagamento: debito, credito, beneficio, dinheiro/outro e transferencia.

## Fora de Escopo

- Reescrever todo o dominio de transacoes.
- Remover models atuais.
- Implementar ML/LLM de classificacao.
- Criar conciliacao bancaria automatica.

## Estado Atual

O app ja possui lancamentos, cartoes, faturas, transferencias e parcelamentos. O fluxo de criacao ainda expõe mais o modelo interno do que a intencao do usuario.

## Comportamento Esperado

- O formulario pergunta a forma de pagamento.
- Credito habilita cartao e campos de parcelamento.
- Beneficio habilita cartao/beneficio e modalidade quando aplicavel.
- Debito/dinheiro habilita conta.
- Transferencia pode ser iniciada pelo mesmo ponto de entrada, mas cria `Transfer`.
- Filtros de lancamentos continuam dinamicos e persistentes por query string.
- Lancamentos podem ser editados com regras explicitas.

## Telas e Componentes

Telas afetadas:

- lista de transacoes;
- criacao de transacao;
- edicao de transacao;
- possivel formulario unificado de lancamento;
- filtros de transacoes.

Estados dinamicos:

- campos de cartao;
- campos de conta;
- campos de beneficio;
- campos de parcelamento;
- campos de transferencia.

## Regras de Negocio

- Forma de pagamento e uma decisao de UX e pode ser traduzida pela camada de form/service para os models atuais.
- Compra no credito pode criar compra de cartao e parcelamento.
- Transferencia nao conta como receita nem despesa.
- Editar lancamento pago deve recalcular ou bloquear alteracoes conforme regra explicita.
- Compra vinculada a fatura deve respeitar status da fatura.

## Dados, Services e Selectors

Criar ou evoluir:

- form dinamico de lancamento;
- service orquestrador para lancamento por forma de pagamento;
- selectors para filtros dinamicos;
- services de edicao com impacto financeiro claro.

## Estados de Erro

- Credito sem cartao deve gerar erro de form.
- Debito sem conta deve gerar erro de form.
- Parcela invalida deve aparecer no contexto do parcelamento.
- Transferencia para a mesma conta deve ser bloqueada.
- Edicao de lancamento pago deve informar impacto ou restricao.

## Testes Esperados

- Criar lancamento em debito.
- Criar lancamento em credito.
- Criar lancamento em beneficio.
- Criar lancamento em dinheiro/outro.
- Criar transferencia pelo fluxo de lancamento.
- Criar compra parcelada inline.
- Editar lancamento nao pago.
- Editar lancamento pago conforme regra definida.

## Criterios de Aceite

- Usuario registra credito, debito e beneficio sem entender model interno.
- Compra no credito pode ser parcelada no mesmo fluxo.
- Transferencia pode ser criada sem virar despesa/receita.
- Filtros de lancamento persistem por query string.
- Lancamento pode ser editado com regras explicitas.

## Issues Sugeridas

- Criar form dinamico de lancamento.
- Criar service orquestrador por forma de pagamento.
- Adicionar edicao de lancamento.
- Adicionar parcelamento inline.
- Adicionar filtros dinamicos em lancamentos.
- Adicionar testes de cada forma de pagamento.
- Adicionar testes de edicao.
## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- "Forma de pagamento" e conceito de UX e pode ser traduzido para models existentes.
- O dominio atual de `Transaction`, `Transfer`, `Card` e `InstallmentPlan` deve ser preservado.
- Parcelamento inline cria ou reutiliza entidade de parcelamento.
- Transferencia iniciada pelo lancamento continua sendo `Transfer`.
- Cartoes de beneficio (VT/VR) funcionam como pre-pago com saldo proprio, nao como credito.

## Decisões Tomadas

### Forma de Pagamento como Camada Form/Service

- **Decisão**: Forma de pagamento não será persistida em `Transaction`, apenas camada form/service
- **Justificativa**: Menor impacto em schema, menor risco de regressão, pode ser persistido depois se necessário
- **Risco**: Se precisar persistir depois, será mais complexo

### Cartões de Benefício com Saldo (Pré-pago)

- **Decisão**: Adicionar campo `balance` (Decimal) em Card, diferenciar por `card_type`, criar service para atualizar saldo
- **Justificativa**: VT/VR têm saldo real, compras consomem saldo, recebimentos atualizam saldo
- **Risco**: Migration necessária, compatibilidade com faturas existentes

### Edição de Lançamento Pago Bloqueada

- **Decisão**: Edição de lançamento pago fica bloqueada inicialmente com mensagem clara
- **Justificativa**: Maior segurança, evita corrupção de saldo, UX mais previsível
- **Risco**: Usuário pode querer editar pagos (pode ser backlog)

### Parcelamento Inline MVP

- **Decisão**: Parcelamento inline MVP: apenas parcelas iguais
- **Justificativa**: Simplicidade, reduz complexidade de UI e validação
- **Risco**: Limita casos de uso reais

## Open Questions

- ~~A forma de pagamento deve virar campo persistido em `Transaction` ou apenas camada de form/service?~~ **DECIDIDO: camada form/service**
- ~~Compra no beneficio deve usar `Card`, `FinancialAccount` ou um subtipo especifico?~~ **DECIDIDO: Card com campo balance para pré-pago**
- ~~Edicao de lancamento pago recalcula saldo, cria ajuste ou fica bloqueada inicialmente?~~ **DECIDIDO: bloqueada inicialmente**
- ~~Parcelamento inline deve permitir entrada/sinal ou apenas parcelas iguais?~~ **DECIDIDO: apenas parcelas iguais (MVP)**

## Task Breakdown Inicial

- [ ] Task: Adicionar saldo e comportamento pre-pago para cartoes de beneficio.
  - Acceptance: Card tem campo balance, recebimento atualiza saldo, compra consome saldo.
  - Verify: testes de model e service para balance.
  - Files: `cards/models.py`, `cards/migrations/`, `cards/services.py`, `cards/tests/`.
- [ ] Task: Definir contrato do form dinamico.
  - Acceptance: campos obrigatorios por forma de pagamento ficam especificados.
  - Verify: revisao da spec/issue antes de model changes.
  - Files: `transactions/forms.py`, spec da issue.
- [ ] Task: Criar service orquestrador por forma de pagamento.
  - Acceptance: debito, credito, beneficio e dinheiro/outro criam registros corretos.
  - Verify: testes de service por forma de pagamento.
  - Files: `transactions/services.py`, `transactions/tests/`.
- [ ] Task: Adicionar parcelamento inline.
  - Acceptance: compra no credito pode criar parcelamento no mesmo fluxo.
  - Verify: testes de service e view.
  - Files: `transactions/forms.py`, `transactions/views.py`, `installments/services.py`.
