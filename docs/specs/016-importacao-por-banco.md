# Spec 016 - Importacao por Banco

Herda a baseline da spec 000, as regras de importacao das specs 006 e 014 e a ADR-012 (GET nunca grava, `full_clean`, erros via `core/errors.py`). Entrega da Etapa 2 do plano-mestre (Confluence, espaco FIN, pagina 950274).

Issues: #269 (FIN-46), #268 (FIN-45, perfis de CSV, secao P2 abaixo).

## Contexto

O OFX bancario traz o banco (`BANKID`), a conta (`ACCTID`) e o tipo (`ACCTTYPE`) em `BANKACCTFROM`. Hoje isso e ignorado e o usuario escolhe a conta a mao a cada upload, ou deixa as linhas "sem conta".

## Objetivo

- Ao enviar um OFX bancario sem escolher conta, o app reconhece o banco pelo `Institution.code` e sugere a conta quando houver exatamente uma candidata.
- O usuario ve qual banco foi identificado.

## Decisoes

| Tema | Decisao |
| ---- | ------- |
| Schema | Nenhuma migration. `Institution.code` ja existe. |
| `ACCTID` | Usado so no upload, exibido mascarado (ultimos 4 digitos) na mensagem. Nao e persistido (sem campo novo, sem ADR). |
| Comparacao de `BANKID` | So digitos, sem zeros a esquerda (`0260` == `260`). Mais de uma instituicao casando = sem identificacao. |
| `ACCTTYPE` | `CHECKING` ou ausente -> `checking`; `SAVINGS` -> `savings`; outro valor -> banco identificado, sem conta sugerida. |
| Candidatas | Contas ativas, de instituicao ativa, da instituicao identificada e do tipo mapeado. Exatamente uma -> sugerida; zero ou varias -> sem sugestao. |
| Cartao | So `BANKACCTFROM` e lido; `CCACCTFROM` e ignorado (OFX de cartao importa como hoje). |
| Varias contas no arquivo | Mais de um `BANKACCTFROM` distinto = ambiguo, sem deteccao. |
| Precedencia | A conta escolhida no upload prevalece sobre a detectada. |
| Momento | So no staging (POST de upload). Linhas ja gravadas nao sao reavaliadas; GET nao grava. |
| Exibicao | `messages.info` na tela; chave `bank_detection` (ou `null`) no JSON 201 da API. |
| Fora de escopo | Deteccao de banco em CSV/XLSX (o CSV por banco e a P2 abaixo, escolhido pelo usuario). |

## Criterios (EARS)

- QUANDO um OFX com `BANKID` casando uma unica instituicao ativa for enviado sem conta E houver exatamente uma conta candidata, ENTAO as linhas SHALL ser gravadas com essa conta sugerida.
- QUANDO o usuario escolher uma conta no upload, ENTAO a conta escolhida SHALL prevalecer.
- QUANDO houver zero ou varias candidatas, ou `ACCTTYPE` fora do mapa, ENTAO as linhas SHALL ficar sem conta e o banco identificado SHALL ser informado.
- QUANDO o OFX nao tiver `BANKACCTFROM`/`BANKID`, ou o banco nao casar, ENTAO o comportamento SHALL ser o atual.
- A deteccao SHALL NOT gravar nada fora do staging nem persistir `ACCTID`.

## Testes

- Importer: extrai `BANKID`/`ACCTID`/`ACCTTYPE` (tags fechadas e abertas), ignora cartao, ambiguo, ausente.
- Selector: uma, zero e duas contas; zeros a esquerda; inativas; tipo.
- Service: precedencia da conta escolhida.
- Views HTML e JSON: sugestao, mensagem, `bank_detection`, regressao sem banco.

## P2: Perfis de CSV por banco (#268, FIN-45)

Importar o CSV exportado pelo Nubank e pelo Inter sem editar o arquivo. Cada banco tem um perfil de layout declarado em codigo (`CsvProfile` em `imports/importers.py`). O CSV generico da spec 014 nao muda.

### Decisoes

| Tema | Decisao |
| ---- | ------- |
| Escolha do perfil | Campo opcional `csv_profile` no upload (tela e API): `generic` (padrao quando ausente ou vazio), `nubank`, `inter`. Sem deteccao automatica; o erro do CSV generico sugere escolher o banco. |
| Schema | Nenhuma migration. `source_type` gravado continua `csv`; o perfil nao e persistido. |
| Combinacoes invalidas | `csv_profile` desconhecido: 400 "Perfil de CSV nao suportado". Perfil de banco com `source_type` diferente de `csv`: 400 "Perfil de banco so se aplica a CSV". XLSX e OFX nao mudam. |
| Nubank | `,`, cabecalho `Data, Valor, Identificador, Descricao` (todas obrigatorias), `dd/mm/aaaa`, valor com ponto e sinal. `Identificador` vira `external_id`. |
| Inter | `;`, metadados antes do cabecalho, cabecalho `Data Lancamento, Historico, Descricao, Valor` (obrigatorias) e `Saldo` (opcional, ignorado), valor com virgula e sinal, sem `external_id`. |
| Cabecalho | Entre as 10 primeiras linhas nao vazias, vale a que casa mais colunas obrigatorias (empate: a primeira). As anteriores sao metadados e ficam de fora (bloco Conta, Periodo e Saldo do Inter nao sao lidos). Numero de linha dos erros e o fisico do arquivo. |
| Nomes e celulas | Colunas comparadas sem caixa, sem acento e sem espacos nas pontas; celulas passam por strip. Colunas extras desconhecidas sao ignoradas. BOM ja e removido na leitura. |
| Sinal | Valor com sinal (negativo e despesa), como no generico, reaproveitando `_parse_date` e `_parse_amount`. |
| Descricao do Inter | `"<Historico> - <Descricao>"`; se uma das partes for vazia, so a outra; espacos colapsados; corte em 255 caracteres (`raw_description`). O formato faz parte do hash de deduplicacao e da chave de historico de categoria: mudar depois quebra a deduplicacao de arquivos ja importados. |
| Deduplicacao do Inter | Hash atual (origem, data, valor, descricao normalizada) com a regra de ocorrencias; sem usar o `Saldo`. |
| Saldo | Ignorado: sem conferencia de saldo corrente nem persistencia. |
| Mensagem de erro | `CSV do <Banco> sem colunas: <nomes como o banco escreve>. Confira se escolheu o banco certo.` (400 na API, `messages.error` na tela, sem gravar). Arquivo de outro banco cai na mesma mensagem. |
| Fixtures | `imports/tests/fixtures/csv/nubank_extrato.csv` e `inter_extrato.csv`, totalmente sinteticas (preservam o layout, inclusive espacos no fim). Extrato real nunca entra no repositorio (spec 014). |

### Criterios (EARS)

- QUANDO um CSV no layout do Nubank for enviado com `csv_profile=nubank`, ENTAO as linhas SHALL ser gravadas em staging com data, valor, tipo pelo sinal, descricao e `external_id` do Identificador.
- QUANDO um CSV no layout do Inter (metadados, `;`, virgula decimal, espacos sobrando) for enviado com `csv_profile=inter`, ENTAO as linhas SHALL ser gravadas com a descricao `Historico - Descricao` e sem `external_id`.
- SE faltar uma coluna obrigatoria do perfil, ENTAO o arquivo SHALL ser recusado com mensagem que cita a coluna, sem gravar linhas.
- SE o arquivo for de outro banco que o do perfil, ENTAO o arquivo SHALL ser recusado como acima, sugerindo conferir o banco.
- QUANDO `csv_profile` estiver ausente ou for `generic`, ENTAO o comportamento SHALL ser o da spec 014.
- SE `csv_profile` for desconhecido, ou de banco com `source_type` diferente de `csv`, ENTAO a resposta SHALL ser 400 / `messages.error`, sem gravar.
- O sistema SHALL NOT usar a coluna Saldo nem os metadados do Inter.

### Testes

- Importer: amostra de cada banco, BOM, coluna faltando (Identificador, Historico, Valor), perfil errado, coluna extra, Saldo opcional, fallbacks e corte da descricao do Inter, sentinela dos espacos e metadados da fixture, equivalencia com o generico no Nubank, factory e dica no generico.
- Service: reimportar o extrato do Inter marca tudo como duplicado; duas linhas identicas com uma ja importada marcam so uma.
- Views HTML e JSON: perfil valido, coluna faltando, perfil desconhecido, perfil com OFX, sem perfil igual ao generico, GET lista os perfis e nao grava.

### Pendencia de homologacao

Comparar o MEMO do OFX do Inter com o formato `Historico - Descricao` antes de depender da deduplicacao cruzada CSV x OFX (hoje o hash inclui a origem, entao nao ha deduplicacao entre formatos).
