# controle-financeiro

App Django de controle financeiro pessoal, single-user, rodando localmente via Docker Compose.

## Comandos

Use `venv/bin/python` quando o ambiente virtual não estiver ativado.

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Onde estão as regras

- Baseline de código, testes e boundaries: `docs/specs/000-sdd-baseline.md`.
- Padrões de arquitetura (GET não grava, invariantes, `full_clean`, lock, `core/errors.py`, datas): ADR-012.
- Specs executáveis: `docs/specs/NNN-*.md`.
- Plano-mestre, ADRs e histórico: Confluence, espaço FIN
  (https://lucasdevlop94-1792776715909.atlassian.net/wiki/spaces/FIN).
- Tickets: Jira, projeto FIN (épico por módulo, versão por etapa E0–E4). Issues no GitHub são a especificação detalhada.

## Fluxo de entrega

Siga `.agents/AGENTS.md`: task review → implementação → draft do PR.

- Branches `feat/*`, `fix/*`, `docs/*`, `chore/*`, `refactor/*`; PR com squash merge e título em Conventional Commits (spec 009).
- Commits e PRs sem atribuição a ferramentas de IA.
- Decisão de arquitetura tomada numa task review vira ADR no Confluence.
