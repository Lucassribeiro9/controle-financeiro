---
name: controle-financeiro-code-review
description: Code review especializado para o app Controle Financeiro. Use ao revisar PRs, specs implementadas, diffs, refatoracoes, testes, fluxos Django, regras de saldo, faturas, transferencias, recorrencias, importacoes, metas, seguranca, UX financeira ou aderencia a SDD.
---

# Controle Financeiro Code Review

## Objetivo

Revisar mudancas do Controle Financeiro com foco em bugs, riscos financeiros, regressao de UX, aderencia a spec, testes e manutencao da arquitetura Django do projeto.

## Postura de Review

Priorizar achados concretos. Listar problemas antes de resumo. Cada achado deve indicar arquivo/linha quando possivel, impacto e correcao esperada.

Ordem de severidade:

- P0: corrompe dados financeiros, vaza dados ou quebra fluxo critico.
- P1: saldo, fatura, transferencia, recorrencia ou importacao pode ficar incorreto.
- P2: UX confusa, regra duplicada, teste faltando, manutencao arriscada.
- P3: melhoria pequena, naming, organizacao ou consistencia.

## Checklist Financeiro

Verificar:

- valores usam `Decimal`, nao `float`;
- transferencia nao entra como receita/despesa;
- recorrencia gera previsao, nao pagamento automatico;
- compra no credito consome limite quando aplicavel;
- pagamento de fatura debita a conta correta;
- edicao/cancelamento de transacao paga nao deixa saldo inconsistente;
- status cancelado, ignorado ou previsto nao entra indevidamente em relatorios;
- importacao nao confirma lote sem revisao explicita;
- parser nao desloca colunas vazias;
- beneficio, VR/VA/transporte e cartao comum nao se misturam sem regra clara.

## Checklist Django

Verificar:

- regra de negocio fica em `services.py`, `selectors.py` ou model quando for invariante simples;
- view nao contem regra financeira complexa;
- fluxo HTML usa messages/redirect;
- JSON cru so aparece em endpoint API/async intencional;
- forms validam campos obrigatorios;
- templates nao fazem calculo financeiro;
- migrations sao necessarias e revisadas;
- queries em listagens grandes consideram paginacao ou filtros.

## Checklist SDD

Verificar:

- mudanca corresponde a spec/issue;
- fora de escopo nao foi implementado por acidente;
- assumptions da spec continuam verdadeiras;
- open questions nao foram decididas silenciosamente;
- criterios de aceite foram cobertos;
- tasks pequenas nao viraram refatoracao ampla.

## Checklist de Testes

Exigir teste quando houver:

- funcao ou classe nova;
- service financeiro novo;
- selector novo ou alterado;
- view POST;
- alteracao de saldo, fatura, limite, transferencia, recorrencia ou importacao;
- bug corrigido.

Sinalizar se faltarem:

- teste de sucesso;
- teste de erro/validacao;
- teste de regressao;
- teste de banco vazio para tela de dashboard/home;
- teste de message/redirect em POST.

## Checklist UX/Seguranca

Verificar:

- acoes sensiveis explicam impacto antes de confirmar;
- erros aparecem no contexto da tela;
- estados vazios tem CTA util;
- faturas e pagamentos mostram conta, valor e saldo projetado quando relevante;
- dados financeiros nao ficam expostos sem autenticacao quando a spec envolver deploy;
- settings de producao nao usam `DEBUG=True` ou `SECRET_KEY` fallback.

## Formato de Saida

Usar este formato:

```text
Findings
- [P1] Titulo curto
  Arquivo: caminho:linha
  Problema: ...
  Impacto: ...
  Correcao esperada: ...

Open Questions
- ...

Resumo
- ...

Testes
- Rodados: ...
- Nao rodados: ...
```

Se nao houver achados, dizer claramente:

```text
Nao encontrei problemas bloqueantes. Risco residual: ...
```

## Boundaries

Sempre:

- revisar contra spec e regras financeiras;
- priorizar bug/riscos antes de estilo;
- pedir testes quando a regra muda;
- apontar incertezas como open questions.

Nunca:

- aprovar mudanca que possa corromper saldo sem teste;
- sugerir refatoracao ampla sem vinculo com risco;
- aceitar JSON cru em fluxo HTML sem intencao;
- ignorar ausencia de teste em regra financeira;
- tratar preferencia visual como bug sem impacto claro.
