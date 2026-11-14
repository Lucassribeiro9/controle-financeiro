# Spec 016 - Importacao por Banco

Herda a baseline da spec 000, as regras de importacao das specs 006 e 014 e a ADR-012 (GET nunca grava, `full_clean`, erros via `core/errors.py`). Entrega da Etapa 2 do plano-mestre (Confluence, espaco FIN, pagina 950274).

Issues: #269 (FIN-46). A #268 (perfis de CSV) adiciona a propria historia nesta spec depois.

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
| Fora de escopo | CSV/XLSX, perfis de CSV (#268). |

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
