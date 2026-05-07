# Controle Financeiro

Aplicativo web local para controle financeiro pessoal com Django.

## Índice

- [Controle Financeiro](#controle-financeiro)
  - [Índice](#índice)
  - [Visão Geral](#visão-geral)
  - [Stack e Execução](#stack-e-execução)
  - [Fase 1 - Fundação](#fase-1---fundação)
  - [Fase 2 - Cadastros Fundamentais](#fase-2---cadastros-fundamentais)
  - [Documentação Detalhada](#documentação-detalhada)
  - [Roadmap](#roadmap)

## Visão Geral

O projeto segue como referencia:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## Stack e Execução

- Linguagem: Python
- Framework: Django
- Banco inicial: SQLite
- Ambiente local: Docker Compose
- CI: GitHub Actions

Comandos base:

```bash
docker compose up --build
```

```bash
python3 manage.py test
```

## Fase 1 - Fundação

Status: concluída

Implementado:

- Projeto Django inicial
- App `core`
- Dockerfile e `docker-compose.yml`
- Workflow de CI inicial
- Health check com teste automatizado

## Fase 2 - Cadastros Fundamentais

Status: em andamento

Implementado até agora:

- App `institutions`
- Model `Institution`
- Admin de `Institution`
- Testes de model para `Institution`

## Documentação Detalhada

Para detalhes técnicos da fase concluída:

- `docs/phases/fase-1-fundacao.md`

## Roadmap

Os próximos passos seguem o plano de implementação:

- `docs/plans/controle-financeiro-implementation-plan.md`
