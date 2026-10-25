# Ordem de entrega das issues abertas

Tabela de dependências e de conflitos para decidir o que roda em paralelo.

**Fonte:** issues abertas no GitHub em 25/10/2026. O GitHub não tem "blocked by" configurado nestas issues, então as dependências abaixo foram tiradas do texto de cada issue. Confirme na task review antes de iniciar uma onda.

## Regras de paralelismo

- Uma issue por branch e por worktree (`.github/BRANCHING.md`).
- Duas issues só rodam em paralelo se não tocam os mesmos arquivos da coluna "Conflita com".
- Issue que altera migration roda sozinha no momento da migration (numeração de migrations).
- Issues cross-cutting (validação e views compartilhadas) rodam sozinhas.

## Tabela

| Issue | Tipo | Etapa | Depende de | Conflita com (arquivos) | Pode rodar junto com |
| --- | --- | --- | --- | --- | --- |
| #217 confirmar assinatura no cartão como compra | bug | — | — | `recurrences/views.py`, `transactions/services.py` | #232, #238, #230 |
| #218 alinhar previsões sem vínculo | bug | — | #220 (constantes e `related_name`) | `recurrences/views.py`, `core/selectors.py` | #232, #238, #240 |
| #220 nomes de constantes e `related_name` | refactor | — | — | `transactions/constants.py`, `reports/selectors.py`, `core/selectors.py`, `recurrences/` | #232, #237 |
| #230 status de metas desatualizado | bug | — | — | `goals/views.py`, `goals/services.py` | #229, #232, #240 |
| #236 meta de acumulação em risco na home | bug | — | #230 | `core/selectors.py`, `goals/services.py` | #229, #238 |
| #229 contagem de subcategorias no join | bug | — | — | `categories/selectors.py` | #230, #238 |
| #228 metas de redução duplicadas no insights | bug | — | — | `insights/services.py` | #229, #232 |
| #232 form de meta por categoria | bug | — | — | `categories/forms.py`, `categories/views.py` | #217, #220, #228 |
| #238 consultas repetidas no painel | bug | — | — | `reports/selectors.py` | #229, #236 |
| #237 mensagens de validação nas views | bug | — | — | todas as `views.py` | nenhuma (cross-cutting) |
| #225 validar período da URL com helper | bug | — | — | todas as views com período | nenhuma (cross-cutting) |
| #240 tabelas no celular | bug | — | — | `static/css/app.css` | #230, #217 (não CSS) |
| #242 filtros recolhíveis no celular | enhancement | — | #240 | `static/css/app.css`, templates de lista | #217, #230 |
| #241 revisão de importações no celular | bug | — | #240 | `static/css/app.css`, `imports/templates/imports/review.html` | #217, #230 |
| #267 sugerir categoria pelo histórico | enhancement | 1 | — | `imports/services.py` | #265, #266 |
| #266 revisão abre nas pendentes, com abas | enhancement | 1 | — | `imports/selectors.py`, `imports/views.py`, `imports/templates/imports/review.html` | #265, #267 (não `services.py`) |
| #265 origem do lançamento por tipo | enhancement | 1 | — | `transactions/forms.py`, `transactions/services.py` | #266, #267 |
| #243 rotinas periódicas por comando diário | bug | 2 | #217, #218, #230 | `core/management/commands/`, `cards/views.py`, `goals/views.py`, `recurrences/services.py` | nenhuma (mexe em GETs de várias telas) |
| #269 banco do OFX e conta sugerida | enhancement | 2 | #267 (mesmo ponto de sugestão), possível migration se guardar `ACCTID` | `imports/importers.py`, `imports/services.py` | #268 só se não tocar importer |
| #268 perfis de CSV por banco | enhancement | 2 | #269 (importer) | `imports/importers.py` | nenhuma com #269 |

## Ondas sugeridas

Ordem de execução. Dentro de cada onda, as issues que podem rodar juntas estão na coluna "Pode rodar junto com".

1. **Base de dados e recorrências:** #220, depois #217 e #218 (uma por vez, mesma área), e #230.
2. **Metas e painel:** #236 e #229, #228, #238 (em paralelo, arquivos diferentes).
3. **Validação transversal (sozinha):** #237, depois #225. Não rodar junto com outras views.
4. **Celular (uma por vez, mesmo CSS):** #240, depois #241 e #242.
5. **Etapa 1 (importação e lançamentos):** #267, #265, #266 (#267 e #265 em paralelo; #266 pode ir junto).
6. **Etapa 2:** #243 (após a onda 1), #269 (após #267), #268 (após #269).

## Pontos a confirmar na task review

- Se #269 vai guardar `ACCTID` no schema (gera migration).
- Se #265 altera schema (a issue diz que não).
- Se #243 deve ser a mesma issue que a ADR-013 (rotinas periódicas) ou exige uma ADR antes.
- Em qual entrega do Jira (E0–E4) cada issue cai. Esta tabela não tem essa informação.
