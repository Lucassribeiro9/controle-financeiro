# SDD Roadmap

## Objetivo

Organizar a proxima fase do Controle Financeiro com specs pequenas, testaveis e rastreaveis.

O projeto deixa de evoluir por features amplas e passa a evoluir por decisoes documentadas, issues pequenas, branches curtas, PRs revisaveis e squash merge.

## Regra

Nenhuma mudanca relevante entra sem spec minima aprovada.

Uma spec minima deve dizer:

- qual problema resolve;
- o que fica fora;
- quais telas, models, services e selectors entram;
- quais regras de negocio nao podem ficar ambiguas;
- quais testes provam que a mudanca funciona;
- quais criterios encerram a entrega.

As specs numeradas herdam a baseline comum de `docs/specs/000-sdd-baseline.md`, que centraliza comandos, estrutura do projeto, estilo de codigo, estrategia de testes e boundaries.

## Workflow Gated

O fluxo SDD do projeto passa a ser:

```text
SPECIFY -> PLAN -> TASKS -> IMPLEMENT
```

Cada etapa precisa estar clara antes da proxima:

- **Specify**: requisitos, assumptions, comportamento esperado, fora de escopo e open questions.
- **Plan**: componentes afetados, dependencias, riscos e ordem de implementacao.
- **Tasks**: issues pequenas, com aceite, verificacao e arquivos provaveis.
- **Implement**: uma issue por branch curta, com testes e PR.

## Fluxo

1. Atualizar `docs/plans/scope.md` quando a decisao muda produto.
2. Criar spec numerada em `docs/specs/`.
3. Quebrar a spec em issues pequenas.
4. Implementar cada issue em branch curta.
5. Validar com testes e CI.
6. Atualizar documentacao da fase.
7. Fazer squash merge mantendo Conventional Commits.

## Ordem das Specs

1. `001-home-operacional.md` - transformar `/` em uma home acionavel.
2. `002-ux-ui-design-system.md` - formalizar linguagem visual e componentes.
3. `003-feedback-validacoes-confirmacoes.md` - padronizar messages, redirects e confirmacoes.
4. `004-lancamentos-forma-pagamento.md` - tornar lancamentos naturais por forma de pagamento.
5. `005-cartoes-faturas-limites.md` - melhorar cartoes, faturas, limites e pagamentos.
6. `006-importacoes-revisao-em-lote.md` - tornar revisao de importacoes mais rapida.
7. `007-categorias-metas-limites.md` - conectar categorias a metas e limites.
8. `008-estabilizacao-tecnica.md` - reduzir riscos tecnicos antes de integracoes maiores.
9. `009-gitflow-pr-issue-standard.md` - padronizar issues, commits, branches e PRs.
10. `010-seguranca-autenticacao-deploy.md` - preparar seguranca, autenticacao e deploy futuro.

## Ordem de Execucao Recomendada

1. Atualizar `scope.md`.
2. Criar `docs/plans/sdd-roadmap.md`.
3. Criar `docs/specs/009-gitflow-pr-issue-standard.md`.
4. Criar templates de issue e PR.
5. Criar `docs/specs/001-home-operacional.md`.
6. Criar issues da home.
7. Implementar home operacional.
8. Criar `docs/specs/003-feedback-validacoes-confirmacoes.md`.
9. Implementar padronizacao de feedback nos fluxos mais visiveis.
10. Criar `docs/specs/004-lancamentos-forma-pagamento.md`.
11. Implementar lancamento mais natural e parcelamento inline.
12. Seguir para cartoes/faturas, importacoes, categorias e estabilizacao.

## Motivo da Ordem

GitFlow e templates ajudam todas as specs seguintes.

Home da norte visual e operacional.

Feedback evita UX quebrada em todos os fluxos.

Lancamentos e cartoes sao o coracao do uso diario.

Estabilizacao tecnica entra antes de integracoes maiores.

## Criterios Para Quebrar Specs Em Issues

Uma issue deve ser pequena o bastante para virar um PR claro.

O checklist operacional para abrir issues SDD fica em `docs/specs/000-sdd-baseline.md`.

Boa issue:

- muda um fluxo ou componente especifico;
- tem teste claro;
- tem criterio de aceite objetivo;
- pode ser revisada em um diff curto.

Evitar:

- melhorar UX;
- refatorar importacoes;
- arrumar dashboard;
- implementar home completa.

Preferir:

- criar selector da home operacional;
- adicionar cards de resumo na home;
- converter acoes de insights para messages/redirect;
- adicionar limite disponivel na lista de cartoes;
- permitir categoria em lote na revisao de importacoes.

## Test Plan Global

Para cada spec implementada:

- rodar `python manage.py test`;
- rodar `python manage.py check`;
- rodar `python manage.py makemigrations --check --dry-run`;
- criar testes para qualquer funcao ou classe nova;
- criar testes de views para fluxos POST importantes;
- verificar manualmente a tela no navegador quando a spec for UX/UI;
- validar responsividade basica em desktop e mobile;
- confirmar que nao ha JSON cru em fluxo HTML, salvo endpoint intencional.

Observacao local:

- no ambiente atual, os comandos `python manage.py ...` dependem do `venv` ativado;
- sem o `venv` ativado, usar `venv/bin/python manage.py ...` para executar a validacao equivalente.

## Assumptions

- O projeto continua usando Django templates, Chart.js e interatividade leve.
- O app segue single-user/local por enquanto.
- Deploy publico nao e prioridade imediata.
- `feat/*` sera o padrao real de branch daqui para frente.
- A previa `ui-preview-monarch-maybe-rocket.html` e referencia aprovada para a home operacional.
- O foco imediato e SDD, UX operacional e consistencia, nao novas integracoes externas.
