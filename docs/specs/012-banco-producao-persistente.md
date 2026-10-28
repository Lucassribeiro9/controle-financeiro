# Spec 012 - Banco de Producao Persistente e Backup

Herda a baseline da spec 000. Implementa a ADR-008 (Confluence, espaco FIN). Issue GitHub #233, Jira FIN-23.

## Contexto

Em producao o SQLite fica em `/app/db.sqlite3`, dentro da camada gravavel do container, e o `docker-compose.prod.yml` nao monta volume. Recriar o container (`up --build`) apaga todos os dados. Com 2 workers do gunicorn, escritas simultaneas no SQLite podem gerar `database is locked`.

## Objetivo

Os dados financeiros sobrevivem a rebuild, recriacao e `down`/`up`, com backup consistente e restauracao documentada.

## Fora de Escopo

- Postgres (ADR-008 escolheu SQLite).
- Agendamento automatico do backup: o agendador do ADR-013 (servico `scheduler`, rotina `daily_maintenance`) cobre previsoes, faturas, metas e insights; o backup segue no cron do host por ora.
- Copia de backup para fora da maquina.
- Mudanca de schema ou migrations.
- Mudanca no banco de desenvolvimento.

## Comportamento Esperado

- `project/settings/prod.py` le o caminho do banco de `DJANGO_DB_PATH`, com padrao `/data/db.sqlite3`. Dev continua com `BASE_DIR / "db.sqlite3"`.
- O banco de producao usa `journal_mode=WAL` e busy timeout de 20 s. O gunicorn mantem 2 workers.
- O compose de producao monta o volume nomeado `controle-financeiro-data` em `/data`; a imagem cria `/data` com dono `app`.
- O comando `python manage.py backup_db` copia o banco com a API de backup do SQLite (consistente com o app rodando) para `<pasta do banco>/backups/db-AAAAMMDD-HHMMSS.sqlite3` e mantem as 14 copias mais recentes.
- O README documenta variavel, backup, cron diario no host via `docker compose exec`, restauracao e o aviso de que `docker compose down -v` apaga volume e backups juntos.

## Regras

- `backup_db` nunca copia o arquivo cru (WAL pode estar fora do arquivo principal).
- A retencao so remove arquivos com o padrao de nome do comando.
- O comando falha com mensagem clara se o banco nao for SQLite.
- Datas do nome usam `timezone.localtime()`.

## Estados de Erro

- Banco que nao e SQLite: `CommandError`.
- Pasta de backup sem permissao: o erro do sistema operacional chega ao usuario.

## Testes Esperados

- Settings de prod: padrao `/data/db.sqlite3`; `DJANGO_DB_PATH` sobrescreve; WAL e busy timeout em `OPTIONS`.
- Settings de dev: continua em `BASE_DIR / "db.sqlite3"`.
- `backup_db`: gera copia legivel com os mesmos dados; nome com data; retencao de 14; ignora arquivos alheios; falha em banco nao SQLite.

## Criterios de Aceite

- [ ] O caminho do banco em producao vem de variavel de ambiente e fica num volume persistente.
- [ ] `docker compose -f docker-compose.prod.yml up -d --build` duas vezes seguidas mantem os dados.
- [ ] O README documenta backup e restauracao do volume, e a restauracao foi testada uma vez.
- [ ] WAL e busy timeout configurados; 2 workers sem `database is locked` no uso normal.
- [ ] `check`, `makemigrations --check --dry-run` e `test` passam.
