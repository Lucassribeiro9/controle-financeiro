# Controle Financeiro

Aplicativo web local para controle financeiro pessoal com Django.

## Índice
- [Controle Financeiro](#controle-financeiro)
  - [Índice](#índice)
  - [Visão Geral](#visão-geral)
  - [Stack e Execução](#stack-e-execução)
  - [Fase 1 - Fundação](#fase-1---fundação)
  - [Fase 2 - Cadastros Fundamentais](#fase-2---cadastros-fundamentais)
  - [Fase 3 - Transações e Transferências](#fase-3---transações-e-transferências)
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

Status: concluída
Status: concluída

Implementado:
Implementado:

- App `institutions`
- Model `Institution`
- Admin de `Institution`
- Testes de model para `Institution`
- App `categories`
- Model `Category` com hierarquia simples
- Admin de `Category`
- Testes de model para `Category`
- App `accounts`
- Model `FinancialAccount` com vínculo a instituição, tipo, moeda e saldo em `Decimal`
- Admin de `FinancialAccount`
- Testes de model para `FinancialAccount`
- App `cards`
- Model `Card` com regras mínimas para cartões de crédito, benefício, transporte e pré-pago
- Admin de `Card`
- Testes de model para `Card`
- Migrations versionadas para os cadastros fundamentais

## Fase 3 - Transações e Transferências

Status: concluída

Implementado:

- App `transactions`
- Model `Transaction`
- Model `Transfer`
- Admin de `Transaction` e `Transfer`
- Serviços `create_transaction` e `create_transfer`
- Regras para movimentação de saldo por tipo de transação
- Regras para transferências internas entre contas
- Testes de model e serviços para transações e transferências
- Migration versionada para o núcleo de movimentações

## Documentação Detalhada

Para detalhes técnicos das fases:
Para detalhes técnicos das fases:

- `docs/phases/fase-1-fundacao.md`
- `docs/phases/fase-2-cadastros-fundamentais.md`
- `docs/phases/fase-3-transacoes-e-transferencias.md`

## Roadmap

Os próximos passos seguem o plano de implementação:

- `docs/plans/controle-financeiro-implementation-plan.md`
