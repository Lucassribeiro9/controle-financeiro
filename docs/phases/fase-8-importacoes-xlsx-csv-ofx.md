# Fase 8 - Importacoes XLSX, CSV e OFX

## Objetivo da fase

Permitir a entrada de dados externos com revisao antes da criacao de transacoes reais.

A importacao deve transformar arquivos financeiros em registros pendentes para conferencia do usuario, evitando confirmacao automatica e reduzindo o risco de duplicidade.

Referencias:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## O que foi criado

### 1. App `imports`

Arquivos principais:

- `imports/apps.py`
- `imports/models.py`
- `imports/admin.py`
- `imports/importers.py`
- `imports/services.py`
- `imports/selectors.py`
- `imports/views.py`
- `imports/urls.py`
- `imports/migrations/0001_initial.py`
- `imports/tests/test_importers.py`
- `imports/tests/test_services.py`
- `imports/tests/test_selectors.py`
- `imports/tests/test_views.py`

Papel do app:

- Centralizar o fluxo de importacao de arquivos externos.
- Normalizar linhas importadas para um formato interno comum.
- Salvar importacoes como pendencias de revisao.
- Permitir confirmacao ou descarte antes de criar transacoes reais.

### 2. Model `ImportedTransaction`

Arquivo:

- `imports/models.py`

Papel do model:

- Representar uma transacao importada aguardando revisao.
- Guardar a origem do arquivo.
- Guardar descricao original e descricao normalizada.
- Guardar valor, data e tipo de transacao sugerido.
- Guardar sugestoes de conta e categoria.
- Guardar identificadores para deteccao de duplicidade.
- Vincular a `Transaction` real quando confirmada.

Campos principais:

- `source_file_name`
- `source_type`
- `raw_description`
- `normalized_description`
- `amount`
- `date`
- `suggested_account`
- `suggested_category`
- `suggested_transaction_type`
- `confirmed_transaction`
- `status`
- `external_id`
- `import_hash`
- `created_at`
- `updated_at`

Status iniciais:

- `pending`
- `confirmed`
- `discarded`
- `duplicate`

Tipos de origem:

- `csv`
- `xlsx`
- `ofx`

Regras iniciais:

- Valor importado deve ser positivo depois da normalizacao.
- Importacao confirmada deve estar vinculada a uma `Transaction`.
- Importacao nao confirmada nao pode ter `confirmed_transaction`.
- Importacao duplicada deve ter `external_id` ou `import_hash`.

### 3. Importers

Arquivo:

- `imports/importers.py`

Importers implementados:

- `CsvTransactionImporter`
- `XlsxTransactionImporter`
- `OfxTransactionImporter`

Estrutura comum:

- Todos retornam uma lista de `ImportedTransactionRow`.
- A linha normalizada possui data, descricao original, descricao normalizada, valor positivo, tipo sugerido e identificador externo opcional.

Campos esperados em CSV e XLSX:

- `date`
- `description`
- `amount`
- `external_id` opcional

Exemplo CSV:

```csv
date,description,amount
2026-05-10,Mercado Dia,-87.45
2026-05-05,Salario,5000.00
```

Exemplo OFX minimo:

```xml
<OFX>
  <STMTTRN>
    <DTPOSTED>20260510</DTPOSTED>
    <TRNAMT>-87.45</TRNAMT>
    <FITID>OFX123</FITID>
    <MEMO>Mercado Dia</MEMO>
  </STMTTRN>
</OFX>
```

Regras de normalizacao:

- Valores negativos viram despesas sugeridas.
- Valores positivos viram receitas sugeridas.
- O valor salvo em `amount` fica sempre positivo.
- Descricoes passam por normalizacao simples de espacos.
- OFX usa `FITID` como `external_id` quando disponivel.
- OFX aceita blocos `STMTTRN` com tags fechadas e variacoes OFX 1.x com tags abertas.
- XLSX e lido sem dependencia externa, usando `zipfile` e XML da biblioteca padrao.

### 4. Services

Arquivo:

- `imports/services.py`

Services implementados:

- `build_import_hash`
- `suggest_category`
- `detect_duplicate_import`
- `detect_duplicate_transaction`
- `stage_imported_transactions`
- `confirm_imported_transaction`
- `discard_imported_transaction`

Comportamento atual:

- `stage_imported_transactions` salva linhas importadas como `pending` ou `duplicate`.
- `build_import_hash` cria uma chave estavel para identificar linhas importadas.
- `detect_duplicate_import` compara importacoes por `external_id` ou `import_hash`.
- `detect_duplicate_transaction` identifica possivel transacao real ja cadastrada.
- `confirm_imported_transaction` cria uma `Transaction` real usando `create_transaction`.
- `discard_imported_transaction` marca a importacao como descartada sem criar transacao real.

Regra importante:

- Confirmar uma importacao usa o fluxo oficial de transacoes e aplica os impactos de saldo ja existentes no projeto.

### 5. Selectors

Arquivo:

- `imports/selectors.py`

Selector implementado:

- `get_imported_transactions_for_review`

Comportamento:

- Lista importacoes pendentes e duplicadas por padrao.
- Permite filtrar por status quando necessario.
- Usa `select_related` para carregar conta, categoria e transacao confirmada.

### 6. Views e rotas

Arquivos:

- `imports/views.py`
- `imports/urls.py`

Rotas implementadas:

- `imports/upload/`
- `imports/review/`
- `imports/<int:imported_transaction_id>/confirm/`
- `imports/<int:imported_transaction_id>/discard/`

Fluxo:

1. Usuario envia arquivo por upload.
2. Importer normaliza as linhas do arquivo.
3. Service cria registros `ImportedTransaction`.
4. Usuario revisa importacoes pendentes ou duplicadas.
5. Usuario confirma ou descarta cada item.
6. Somente itens confirmados viram `Transaction`.

## Regras importantes

- Importacoes nao viram transacoes reais automaticamente.
- Linhas importadas entram como pendentes para revisao.
- Duplicidades podem ser identificadas por `external_id` ou `import_hash`.
- Valores negativos sao tratados como despesas sugeridas.
- Valores positivos sao tratados como receitas sugeridas.
- OFX usa `FITID` como identificador externo quando disponivel.
- O model `ImportedTransaction` e generico para CSV, XLSX e OFX.

## Testes implementados na fase

### Importers

Arquivo:

- `imports/tests/test_importers.py`

Cobertura:

- Leitura de CSV valido com receita e despesa.
- Captura de `external_id` em CSV.
- Ignorar linhas vazias.
- Rejeicao de colunas obrigatorias ausentes.
- Rejeicao de data invalida.
- Rejeicao de valor invalido.
- Rejeicao de valor zerado.
- Leitura de bytes com BOM UTF-8.
- Normalizacao de descricao.
- Leitura de XLSX simples.
- Rejeicao de XLSX sem colunas obrigatorias.
- Leitura de OFX com tags fechadas.
- Leitura de OFX 1.x com tags abertas.
- Rejeicao de OFX sem valor.
- Selecao de importer por tipo de origem.

### Services

Arquivo:

- `imports/tests/test_services.py`

Cobertura:

- Geracao estavel de hash de importacao.
- Criacao de importacoes pendentes.
- Marcacao de duplicidade por hash.
- Deteccao de duplicidade por identificador externo.
- Confirmacao de importacao criando `Transaction`.
- Exigencia de tipo de transacao quando nao ha sugestao.
- Descarte de importacao sem criar `Transaction`.

### Selectors

Arquivo:

- `imports/tests/test_selectors.py`

Cobertura:

- Listagem de importacoes pendentes e duplicadas para revisao.
- Filtro explicito por status.

### Views

Arquivo:

- `imports/tests/test_views.py`

Cobertura:

- Upload criando importacoes pendentes.
- Rejeicao de upload sem arquivo.
- Rejeicao de tipo desconhecido.
- Upload OFX.
- Listagem de importacoes para revisao.
- Confirmacao criando `Transaction`.
- Exigencia de conta na confirmacao.
- Descarte sem criar `Transaction`.

Execucao local:

```bash
python3 manage.py test imports
```

Ou pelo ambiente Docker:

```bash
docker compose run --rm web python manage.py test imports
```

## Status da fase

Fase 8 concluida conforme o escopo previsto de importacoes XLSX, CSV e OFX com revisao antes da confirmacao.

Itens de evolucao permanecem para ciclos seguintes:

- Interface HTML dedicada para upload e revisao.
- Regras configuraveis de sugestao de categoria.
- Sugestao de cartao alem de conta.
- Reconciliaçao mais avancada com recorrencias.
- Suporte a variacoes adicionais de OFX por banco.
- Tratamento mais completo de planilhas XLSX com multiplas abas.
