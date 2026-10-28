# Spec 015 - Formulario de Lancamento

Herda a baseline da spec 000 e os padroes de interface da spec 002. Entrega 1.4 da Etapa 1 do plano-mestre (Confluence, espaco FIN, pagina 950274). A P1 (#239) e so de CSS e nao envolve regra financeira. A P2 (#265) envolve regra financeira (saldo de cartoes) e segue a ADR-012 e a ADR-015 (Confluence, espaco FIN).

Issues: #239 (FIN-30), #265 (FIN-42).

## Contexto

`static/js/app.js` esconde os campos condicionais dos formularios de lancamento e de cartao com `container.hidden = true` e `field.disabled = true`. A regra `.form-field { display: grid; }` em `static/css/app.css` tem prioridade sobre o `display: none` padrao do atributo `[hidden]`, e o CSS nao tem uma regra global para `[hidden]`. Resultado: no lancamento em debito, Conta origem, Conta destino, Cartao e Parcelas continuam visiveis como selects desabilitados. Conferido no navegador em `/transactions/create/` (os quatro containers com `hidden=true` e `display: grid`).

## Objetivo

- Os formularios de lancamento e de cartao mostram so os campos da opcao escolhida (forma de pagamento ou tipo de cartao), inclusive na edicao.

## Fora de Escopo

| Item | Motivo |
| ---- | ------ |
| Mudar `static/js/app.js` (P1) | O JS ja alterna `hidden` e `disabled` corretamente; so o CSS impede o efeito. A P2 (#265) muda o JS para filtrar a origem pelo tipo. |
| Layout, tabelas no celular e remodelacao visual | Etapa 3 (ADR-007, ADR-014). |
| Validacao dos campos no servidor | Sem defeito aberto; o servidor ja ignora campos nao usados pela forma de pagamento. |
| Esconder os campos antes do JS carregar | Sem JS o formulario continua completo e funcional; o piscar no carregamento e aceito. |

## Schema

Nenhuma mudanca de schema (P1 e P2). A compra em cartao de saldo reutiliza o tipo `benefit_purchase`; nao ha backfill nem data migration.

- Verify: `python manage.py makemigrations --check --dry-run` sem migrations novas.

## Suposicoes e Questoes Abertas

| Suposicao / decisao | Padrao escolhido | Motivo | Confirmado? |
| ------------------- | ---------------- | ------ | ----------- |
| Onde corrigir | Regra global `[hidden] { display: none !important; }` em `app.css`, como na issue | Corrige a causa (CSS sobrepondo o atributo) para qualquer componente, sem tocar o JS | s |
| Uso de `!important` | Aceito nesta regra | Seletores de componente como `.form-field` e `.import-filter-bar .form-field` tem especificidade maior que `[hidden]`; sem `!important` o problema voltaria em cada componente com `display` proprio | n |
| Teste automatizado | Teste de `SimpleTestCase` que le `app.css` e exige a regra, mais validacao manual no navegador | O projeto nao tem teste de JS/CSS no navegador; o teste impede a remocao silenciosa da regra | n |

| Saldo dos cartoes de transporte e pre-pago (P2, D1) | Estender o saldo proprio `balance` a todo o grupo de saldo (benefit, prepaid, transport); `CardForm.save` copia o saldo informado para `balance`; sem backfill | Um conceito de saldo so e debito atomico igual ao do beneficio (ADR-015) | s |
| Campo de origem (P2, D2) | Select unico `source` com grupos Contas, Cartoes de credito e Cartoes de saldo; valores `account:<id>` e `card:<id>`; o `clean` deriva `payment_method`, `transaction_type`, `account` e `card` | Funciona sem JS; assinatura dos services e a view nao mudam (ADR-015) | s |
| Tipo persistido da compra em cartao de saldo (P2, D3) | Reutilizar `benefit_purchase`, sem migration | Nao muda a definicao de gasto (ADR-005); rotulo na lista fica para issue derivada (E3) | s |
| `Card.clean` (P2) | Continua exigindo saldo estimado so do beneficio | Nao invalidar cartoes existentes no `full_clean` da compra | n |
| Origem inativa na edicao (P2) | A origem salva aparece nas opcoes mesmo se a conta ou o cartao estiver inativo | Permite editar outros campos sem trocar a origem | n |

**Questoes abertas:** nenhuma.

## Historias

### P1: Campos condicionais somem (#239)

**Historia:** Como usuario, quero ver so os campos da forma de pagamento escolhida, para nao me confundir com campos de transferencia e de cartao num lancamento em debito.

**Criterios de Aceite:**

1. O CSS DEVE conter a regra global `[hidden] { display: none !important; }`.
2. QUANDO a forma de pagamento e "Debito" ENTAO o formulario de lancamento DEVE ocultar Conta origem, Conta destino, Cartao e Parcelas e mostrar Conta.
3. QUANDO a forma de pagamento e "Credito" ENTAO o formulario de lancamento DEVE mostrar Cartao e Parcelas e ocultar Conta, Conta origem e Conta destino.
4. QUANDO o tipo do cartao e "Credito" ENTAO o formulario de cartao DEVE mostrar os campos de credito e ocultar os de saldo; QUANDO e beneficio, pre-pago ou transporte ENTAO DEVE mostrar os de saldo e ocultar os de credito.
5. QUANDO o formulario e aberto para edicao ENTAO DEVE aplicar as mesmas regras sobre o valor ja salvo.

**Teste independente:** em `/transactions/create/` com "Debito", `getComputedStyle(container).display` dos quatro campos e `none`; trocar para "Credito" mostra Cartao e Parcelas.

### P2: Origem do lancamento por tipo e cartoes de saldo (#265)

**Historia:** Como usuario, quero escolher o que e o lancamento (receita, despesa ou transferencia) e depois de onde sai ou para onde entra o dinheiro, vendo so as opcoes validas, para lancar salario, compras no credito e compras em vale-refeicao, vale-transporte e cartao pre-pago sem combinacoes incoerentes.

**Criterios de Aceite:**

1. O formulario DEVE ter o campo Tipo (Receita, Despesa, Transferencia) e um campo unico de origem ("Pagar com" na despesa, "Receber em" na receita), no lugar de Forma de pagamento, Conta e Cartao.
2. QUANDO o Tipo e Receita ENTAO a origem DEVE listar so contas e o servidor DEVE recusar cartao com mensagem no campo de origem.
3. QUANDO o Tipo e Despesa ENTAO a origem DEVE listar Contas, Cartoes de credito e Cartoes de saldo (benefit, prepaid, transport); escolher cartao de credito DEVE mostrar Parcelas, escolher conta ou cartao de saldo NAO.
4. O servidor DEVE derivar do valor escolhido a forma de pagamento, o tipo persistido, a conta e o cartao: conta + receita = receita; conta + despesa = despesa; cartao de credito = compra no cartao; cartao de saldo = compra no beneficio.
5. A compra em cartao de transporte, pre-pago ou beneficio DEVE debitar o saldo proprio (`balance`) do cartao de forma atomica e DEVE ser recusada com saldo insuficiente.
6. `CardForm` DEVE copiar o saldo informado para `balance` em cartoes de beneficio, pre-pago e transporte, e a lista de cartoes DEVE mostrar `balance` para o grupo de saldo.
7. Combinacoes invalidas enviadas direto ao servidor (sem JS) DEVEM ser recusadas com mensagem no campo; Parcelamento so e aceito com cartao de credito.
8. A edicao de receita, despesa em conta, compra no credito e compra em cartao de saldo DEVE abrir com Tipo e origem salvos; editar a compra DEVE devolver o saldo anterior e aplicar o novo; Transferencia NAO e opcao na edicao.
9. O JS DEVE filtrar os grupos da origem pelo Tipo, trocar o rotulo e mostrar Parcelas so para cartao de credito; sem JS o formulario continua funcional.

**Teste independente:** em `/transactions/create/` lancar uma compra de R$ 20,00 num cartao de transporte com saldo R$ 50,00 e conferir saldo R$ 30,00 na lista de cartoes; lancar salario em conta e conferir o saldo da conta.

## Regras Transversais

- P1: correcao so em `static/css/app.css`; sem mudanca em views, services, forms ou JS.
- P2: regra de saldo em services com `atomic` e `select_for_update`, `full_clean` antes de `save`, erros via `core/errors.py`; a assinatura de `create_transaction_by_payment_method` e `update_transaction` e a view fina nao mudam (a view so repassa a transacao editada ao form).
- Nenhum GET grava no banco (inalterado).

## Testes Esperados

- Teste de `SimpleTestCase`: `static/css/app.css` contem a regra `[hidden]` com `display: none !important`.
- Validacao no navegador (desktop e celular): lancamento com Debito e Credito (criacao e edicao); cartao com Credito e com tipo de saldo (criacao e edicao).
- P2, form: Tipo x origem validos e invalidos, incluindo cartoes de transporte e pre-pago, parcelas e transferencia na edicao.
- P2, service: compra em cartao de transporte e pre-pago debita o saldo como beneficio; editar devolve e reaplica; saldo insuficiente.
- P2, cartao: `CardForm` copia o saldo para `balance` no grupo de saldo; lista mostra `balance`.
- P2, view: criar e editar cada combinacao; erro de validacao com `messages`; edicao abre com a origem salva.
- P2, navegador (desktop e 375px): receita, despesa em conta, compra parcelada no credito, compra em VT, pre-pago e VR; criacao e edicao.
- `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test`.

## Ordem de Entrega

1. #239 - regra de CSS, teste e validacao no navegador.
2. #265 - dominio de cartoes de saldo, form de origem, JS e validacao no navegador.

## Rastreabilidade

| Requirement ID | Historia | Issue | Status |
| -------------- | -------- | ----- | ------ |
| FRM-01 | P1: Campos condicionais - AC 1 | #239 | Verified |
| FRM-02 | P1: Campos condicionais - AC 2-3 | #239 | Verified |
| FRM-03 | P1: Campos condicionais - AC 4 | #239 | Verified |
| FRM-04 | P1: Campos condicionais - AC 5 | #239 | Verified |
| FRM-05 | P2: Origem do lancamento - AC 1-4 | #265 | Verified |
| FRM-06 | P2: Origem do lancamento - AC 5 | #265 | Verified |
| FRM-07 | P2: Origem do lancamento - AC 6 | #265 | Verified |
| FRM-08 | P2: Origem do lancamento - AC 7 | #265 | Verified |
| FRM-09 | P2: Origem do lancamento - AC 8 | #265 | Verified |
| FRM-10 | P2: Origem do lancamento - AC 9 | #265 | Verified |

**Cobertura:** 10 requisitos; 4 ligados a #239 (verificados); 6 ligados a #265 (verificados).

## Criterios de Sucesso

- [x] Nenhum campo com atributo `hidden` aparece nos formularios de lancamento e de cartao.
- [x] `check`, `makemigrations --check --dry-run` e `test` passam.
- [x] P2: receita so em conta; despesa em conta, credito ou cartao de saldo; saldo do cartao de saldo debitado; sem JS o formulario recusa combinacoes invalidas.
