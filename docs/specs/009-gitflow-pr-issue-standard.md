# Spec 009 - GitFlow, Issues, Commits e PRs

## Contexto

O projeto precisa manter um fluxo conciso e consistente para que specs, issues, branches, PRs e squash merge formem uma linha de trabalho facil de seguir e revisar.

## Objetivo

Padronizar GitFlow, issues, commits e PRs, criando uma base futura para skill, agent ou subagent de manutencao do fluxo.

## Fora de Escopo

- Automatizar criacao de issues com bot.
- Criar GitHub App.
- Exigir processo pesado para alteracoes pequenas.

## Estado Atual

O CI ja aceita alguns padroes de branch, incluindo `feat/**`. Ainda faltam templates e uma regra documentada para issue, PR e squash commit.

## Comportamento Esperado

- Toda mudanca relevante nasce de spec ou issue.
- Branch curta usa prefixo padronizado.
- PR referencia issue.
- PR tem resumo, testes e checklist.
- Squash commit final segue Conventional Commits.

## Telas e Componentes

Nao se aplica a tela do produto.

Arquivos esperados:

```text
.github/ISSUE_TEMPLATE/feature.yml
.github/ISSUE_TEMPLATE/bug.yml
.github/ISSUE_TEMPLATE/tech-debt.yml
.github/ISSUE_TEMPLATE/ux-ui.yml
.github/PULL_REQUEST_TEMPLATE.md
```

## Regras de Negocio

Nao ha regra financeira. As regras de processo sao:

- usar `feat/*`, `fix/*`, `docs/*`, `chore/*`, `refactor/*`, `test/*`;
- PR deve usar squash merge;
- titulo do PR deve seguir Conventional Commits;
- issue deve ter contexto, objetivo, escopo, fora de escopo, criterios de aceite e testes;
- PR deve ter resumo, issue relacionada, mudancas, como testar e checklist.

## Dados, Services e Selectors

Nao se aplica.

## Estados de Erro

- PR sem teste deve explicar motivo.
- Issue ampla demais deve ser quebrada antes de implementacao.
- Mudanca sem spec deve atualizar scope/spec antes de codar quando alterar produto.

## Testes Esperados

- Validar manualmente se templates aparecem no GitHub.
- Garantir que CI rode em `feat/**`.
- Revisar se o template de PR induz checklist util.

## Criterios de Aceite

- Templates de issue existem.
- Template de PR existe.
- Padrao de branch esta documentado.
- Squash commit final segue Conventional Commits.

## Issues Sugeridas

- Criar templates de issue.
- Criar template de PR.
- Revisar CI para branches `feat/**`.
- Documentar politica de squash merge.
- Criar checklist de Definition of Done para PR.

## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- `feat/*` sera o padrao principal para features.
- Squash merge sera o padrao de integracao.
- Conventional Commits sera usado no titulo final do PR/squash.
- Toda mudanca relevante deve ter issue.

## Decisoes da Spec Review

- Nenhuma alteracao deve ser feita direto na `main`; mesmo mudancas pequenas de documentacao devem entrar por branch e PR.
- Mudancas pequenas de documentacao, como README, podem usar branch `docs/*` sem issue obrigatoria.
- Mudancas de documentacao que alterem produto, scope ou spec devem ter issue.
- Bloqueio de merge sem PR aprovado fica como disciplina manual por enquanto.
- Labels dos templates serao criadas manualmente no GitHub.
- Cada spec deve ter milestone propria quando comecar a gerar issues.

## Open Questions

- Nenhuma pergunta aberta bloqueante nesta spec.

## Task Breakdown Inicial

- [ ] Task: Validar templates no GitHub.
  - Acceptance: feature, bug, tech debt e UX/UI aparecem ao criar issue.
  - Verify: validacao manual no GitHub.
  - Files: `.github/ISSUE_TEMPLATE/*.yml`.
- [ ] Task: Validar template de PR.
  - Acceptance: PR novo mostra checklist esperado.
  - Verify: validacao manual no GitHub.
  - Files: `.github/PULL_REQUEST_TEMPLATE.md`.
- [ ] Task: Documentar politica de squash merge.
  - Acceptance: regra fica clara no README ou doc de contribuicao.
  - Verify: revisao manual.
  - Files: `README.md` ou `docs/plans/sdd-roadmap.md`.
