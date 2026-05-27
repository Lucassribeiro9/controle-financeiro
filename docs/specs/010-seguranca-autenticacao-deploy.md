# Spec 010 - Seguranca, Autenticacao e Deploy Futuro

## Contexto

O app lida com dados financeiros. Mesmo que comece local e single-user, qualquer deploy real exige barreiras de seguranca e configuracao de producao.

## Objetivo

Preparar o projeto para sair do uso local sem expor dados financeiros.

## Fora de Escopo

- Implementar multiusuario completo sem decisao explicita.
- Publicar deploy nesta spec.
- Criar permissao granular por instituicao/conta.
- Migrar dados existentes para owner sem plano aprovado.

## Estado Atual

O projeto esta adequado para desenvolvimento local. Para producao, ainda precisa separar settings, remover fallback inseguro de `SECRET_KEY`, desligar `DEBUG`, configurar hosts e proteger views sensiveis.

## Comportamento Esperado

- Antes de deploy real, login obrigatorio.
- Settings separados ou flags claras para dev/prod.
- `DEBUG=False` em producao.
- `SECRET_KEY` sem fallback inseguro em producao.
- Cookies seguros e HSTS em producao.
- Multiusuario fica fora ate decisao explicita.

## Telas e Componentes

Telas afetadas:

- login;
- logout;
- todas as views financeiras sensiveis;
- possivel tela inicial quando nao autenticado.

## Regras de Negocio

- Dados financeiros nao ficam expostos sem login.
- Uso local pode continuar simples enquanto nao houver deploy real.
- Deploy publico so deve ocorrer com settings de producao validados.
- Multiusuario exige decisao e modelagem propria de ownership.

## Dados, Services e Selectors

Possiveis mudancas futuras:

- settings `dev` e `prod`;
- middleware/decorators de autenticacao;
- owner em models financeiros, caso multiusuario seja aprovado;
- testes de acesso anonimo.

## Estados de Erro

- Acesso anonimo a tela sensivel redireciona para login.
- Variavel obrigatoria ausente em producao falha de forma clara.
- `check --deploy` nao deve ter alertas criticos no settings de producao.

## Testes Esperados

- Views sensiveis exigem login.
- Usuario autenticado acessa telas esperadas.
- Settings de producao nao aceitam `SECRET_KEY` fallback.
- `manage.py check --deploy` com settings de producao passa sem alertas criticos.

## Criterios de Aceite

- `manage.py check --deploy` fica sem alertas criticos em settings de producao.
- Views sensiveis exigem autenticacao.
- Dados financeiros nao ficam expostos sem login.

## Issues Sugeridas

- Criar settings dev/prod.
- Remover fallback inseguro de `SECRET_KEY` em producao.
- Adicionar login/logout.
- Proteger views sensiveis.
- Criar testes de acesso anonimo.
- Rodar `check --deploy` com settings de producao.
## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- O app continua single-user/local ate decisao contraria.
- Deploy publico nao e prioridade imediata.
- Antes de deploy real, login sera obrigatorio.
- Multiusuario exige nova spec de ownership.

## Open Questions

- Login deve entrar mesmo para uso local ou apenas antes de deploy?
- O app tera usuario unico configurado por admin ou cadastro livre?
- Dados ja existentes precisarao de owner quando/ se multiusuario for aprovado?
- Producao usara SQLite inicialmente ou PostgreSQL?

## Task Breakdown Inicial

- [ ] Task: Criar settings dev/prod.
  - Acceptance: producao nao usa `DEBUG=True` nem `SECRET_KEY` fallback.
  - Verify: `python manage.py check --deploy` com settings de producao.
  - Files: `project/settings.py` ou pacote `project/settings/`.
- [ ] Task: Adicionar autenticacao basica.
  - Acceptance: views financeiras sensiveis exigem login.
  - Verify: testes de acesso anonimo/autenticado.
  - Files: views/urls afetadas, `templates/registration/`, testes.
- [ ] Task: Documentar decisao single-user vs multiusuario.
  - Acceptance: scope deixa claro o limite atual e o gatilho para nova spec.
  - Verify: revisao manual.
  - Files: `docs/plans/scope.md`, esta spec.
