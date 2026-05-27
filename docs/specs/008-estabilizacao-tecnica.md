# Spec 008 - Estabilizacao Tecnica

## Contexto

Antes de novas integracoes, e melhor reduzir riscos tecnicos em pontos centrais: status, saldo, importacoes, views grandes, paginacao, testes e tooling.

## Objetivo

Estabilizar a base tecnica para que novas features de UX, integracoes e automacoes sejam mais seguras.

## Fora de Escopo

- Reescrever o projeto.
- Trocar framework.
- Criar arquitetura de microservicos.
- Implementar deploy publico.

## Estado Atual

O projeto possui boa cobertura e organizacao em models, services, selectors e views, mas ja existem pontos que podem divergir ou ficar caros de manter.

## Comportamento Esperado

- CI cobre o padrao real de branch.
- Parser XLSX respeita celulas vazias.
- Recorrencias validam dados antes de persistir.
- Regras de status ficam centralizadas.
- Pagamento de fatura passa pelo mesmo raciocinio de impacto financeiro.
- Views grandes comecam a ser fatiadas.
- Listas grandes ganham paginacao.
- Testes ficam mais baratos de escrever.

## Telas e Componentes

Telas afetadas variam por issue, com prioridade para:

- importacoes;
- transacoes;
- faturas;
- recorrencias;
- relatorios.

## Regras de Negocio

- Status excluidos de relatorios devem vir de fonte unica.
- Impacto de saldo deve ser auditavel.
- Parser nao deve deslocar colunas quando houver celula vazia.
- Refatoracao nao deve alterar comportamento sem teste.

## Dados, Services e Selectors

Itens obrigatorios:

- CI aceitar `feat/**` ou padronizar branch para `feature/**`;
- corrigir importador XLSX para respeitar celulas vazias;
- validar recorrencias com `full_clean()` ou service;
- centralizar status excluidos de relatorios;
- revisar impacto de saldo em pagamento de fatura;
- refatorar `imports/views.py`;
- adicionar paginacao em listas grandes;
- criar factories/helpers de teste;
- adicionar `ruff`, coverage e pre-commit gradualmente.

## Estados de Erro

- Refatoracoes devem preservar mensagens atuais ou melhora-las explicitamente.
- Falhas de parser devem apontar arquivo, linha e campo quando possivel.
- Erros de validacao devem aparecer antes de persistir dado inconsistente.

## Testes Esperados

- Testes de regressao para parser XLSX.
- Testes de status compartilhado.
- Testes de recorrencia invalida.
- Testes de pagamento de fatura.
- Testes de paginacao.
- CI com check, migrations e test.

## Criterios de Aceite

- CI cobre branch padrao real.
- Parser XLSX nao desloca coluna vazia.
- Status de relatorio nao divergem entre apps.
- Views grandes comecam a ser fatiadas.
- Testes ficam mais baratos de escrever.

## Issues Sugeridas

- Ajustar GitHub Actions para `feat/**`.
- Criar constantes compartilhadas de status.
- Corrigir parser XLSX.
- Refatorar bulk actions de importacao para service.
- Criar helpers de testes.
- Adicionar paginacao em transacoes/importacoes.
- Adicionar `ruff` no CI.
## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- A estabilizacao deve preservar comportamento existente.
- Refatoracoes devem ser pequenas e cobertas por testes.
- Tooling novo entra gradualmente.
- Mudanca de saldo ou status exige teste de regressao.

## Open Questions

- `ruff` entra primeiro apenas como check ou tambem format?
- Factories serao helpers simples do projeto ou dependencia externa como factory_boy?
- Centralizacao do motor de saldo deve virar app/servico proprio ou modulo compartilhado?
- Refatorar `imports/views.py` deve ser feito antes ou depois das melhorias de lote?

## Task Breakdown Inicial

- [ ] Task: Centralizar constantes de status.
  - Acceptance: relatorios, goals e insights usam fonte unica para status excluidos.
  - Verify: testes existentes continuam passando.
  - Files: `transactions/constants.py`, selectors afetados, testes.
- [ ] Task: Criar helpers de teste.
  - Acceptance: criacao repetida de contas, cartoes e transacoes fica mais barata.
  - Verify: pelo menos uma suite migra para helper sem perder cobertura.
  - Files: `tests/` ou helpers por app.
- [ ] Task: Refatorar bulk actions de importacao para service.
  - Acceptance: view delega regra de lote ao service.
  - Verify: testes de service e view.
  - Files: `imports/services.py`, `imports/views.py`, `imports/tests/`.
