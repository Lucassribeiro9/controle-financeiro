# Spec 015 - Formulario de Lancamento

Herda a baseline da spec 000 e os padroes de interface da spec 002. Entrega 1.4 da Etapa 1 do plano-mestre (Confluence, espaco FIN, pagina 950274). Nao envolve regra financeira; as ADRs de arquitetura (ADR-012) nao se aplicam.

Issue: #239 (FIN-30).

## Contexto

`static/js/app.js` esconde os campos condicionais dos formularios de lancamento e de cartao com `container.hidden = true` e `field.disabled = true`. A regra `.form-field { display: grid; }` em `static/css/app.css` tem prioridade sobre o `display: none` padrao do atributo `[hidden]`, e o CSS nao tem uma regra global para `[hidden]`. Resultado: no lancamento em debito, Conta origem, Conta destino, Cartao e Parcelas continuam visiveis como selects desabilitados. Conferido no navegador em `/transactions/create/` (os quatro containers com `hidden=true` e `display: grid`).

## Objetivo

- Os formularios de lancamento e de cartao mostram so os campos da opcao escolhida (forma de pagamento ou tipo de cartao), inclusive na edicao.

## Fora de Escopo

| Item | Motivo |
| ---- | ------ |
| Mudar `static/js/app.js` | O JS ja alterna `hidden` e `disabled` corretamente; so o CSS impede o efeito. |
| Layout, tabelas no celular e remodelacao visual | Etapa 3 (ADR-007, ADR-014). |
| Validacao dos campos no servidor | Sem defeito aberto; o servidor ja ignora campos nao usados pela forma de pagamento. |
| Esconder os campos antes do JS carregar | Sem JS o formulario continua completo e funcional; o piscar no carregamento e aceito. |

## Schema

Nenhuma mudanca de schema.

- Verify: `python manage.py makemigrations --check --dry-run` sem migrations novas.

## Suposicoes e Questoes Abertas

| Suposicao / decisao | Padrao escolhido | Motivo | Confirmado? |
| ------------------- | ---------------- | ------ | ----------- |
| Onde corrigir | Regra global `[hidden] { display: none !important; }` em `app.css`, como na issue | Corrige a causa (CSS sobrepondo o atributo) para qualquer componente, sem tocar o JS | s |
| Uso de `!important` | Aceito nesta regra | Seletores de componente como `.form-field` e `.import-filter-bar .form-field` tem especificidade maior que `[hidden]`; sem `!important` o problema voltaria em cada componente com `display` proprio | n |
| Teste automatizado | Teste de `SimpleTestCase` que le `app.css` e exige a regra, mais validacao manual no navegador | O projeto nao tem teste de JS/CSS no navegador; o teste impede a remocao silenciosa da regra | n |

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

## Regras Transversais

- Correcao so em `static/css/app.css`; sem mudanca em views, services, forms ou JS.
- Nenhum GET grava no banco (inalterado).

## Testes Esperados

- Teste de `SimpleTestCase`: `static/css/app.css` contem a regra `[hidden]` com `display: none !important`.
- Validacao no navegador (desktop e celular): lancamento com Debito e Credito (criacao e edicao); cartao com Credito e com tipo de saldo (criacao e edicao).
- `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test`.

## Ordem de Entrega

1. #239 - regra de CSS, teste e validacao no navegador.

## Rastreabilidade

| Requirement ID | Historia | Issue | Status |
| -------------- | -------- | ----- | ------ |
| FRM-01 | P1: Campos condicionais - AC 1 | #239 | Verified |
| FRM-02 | P1: Campos condicionais - AC 2-3 | #239 | Verified |
| FRM-03 | P1: Campos condicionais - AC 4 | #239 | Verified |
| FRM-04 | P1: Campos condicionais - AC 5 | #239 | Verified |

**Cobertura:** 4 requisitos; 4 ligados a #239; 4 verificados (#239).

## Criterios de Sucesso

- [x] Nenhum campo com atributo `hidden` aparece nos formularios de lancamento e de cartao.
- [x] `check`, `makemigrations --check --dry-run` e `test` passam.
