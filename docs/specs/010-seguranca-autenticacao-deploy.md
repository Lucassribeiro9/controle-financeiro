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

- ~~Login deve entrar mesmo para uso local ou apenas antes de deploy?~~ Resolvida na issue #199: sempre.
- ~~O app tera usuario unico configurado por admin ou cadastro livre?~~ Resolvida na issue #199: usuario criado por admin, sem cadastro (por enquanto).
- ~~Dados ja existentes precisarao de owner quando/ se multiusuario for aprovado?~~ Movida para a futura spec de ownership (issue #200).
- Producao usara SQLite inicialmente ou PostgreSQL?

## Decisoes da Issue #201

- Settings em pacote `project/settings/` (`base`, `dev`, `prod`, `validation`).
- `manage.py` usa `dev`; `wsgi.py` e `asgi.py` usam `prod` por padrao.
- Producao exige `DJANGO_SECRET_KEY` (50+ caracteres, 5+ distintos, nao padrao),
  `DJANGO_ALLOWED_HOSTS` e recusa `DJANGO_DEBUG` verdadeiro.
- Estaticos via WhiteNoise; Nginx fica como evolucao futura se necessario.
- Cookies seguros, redirect HTTPS e HSTS de 1 hora por padrao (configuravel);
  `security.W005` e `security.W021` silenciados ate haver deploy HTTPS validado.
- CI roda `check --deploy --fail-level WARNING` e um job que sobe a imagem de producao.

## Decisoes da Issue #199

- `core.auth.ApiAwareLoginRequiredMiddleware` (baseado no `LoginRequiredMiddleware` do
  Django) protege todas as rotas por padrao; fica depois do `AuthenticationMiddleware`.
- Rotas publicas, marcadas com `@login_not_required` ou nativas do Django: `/health/`
  (usado pelo CI) e `/login/`. `/admin/` mantem o login proprio.
- HTML anonimo: 302 para `/login/?next=...`. Views JSON marcadas com
  `@api_login_required` (decorator mais externo): 401 em JSON.
- `login/` e `logout/` ficam em `project/urls.py`, fora do prefixo `accounts/`.
  Logout somente via POST.
- Usuarios sao criados por `createsuperuser`/admin; nao ha cadastro. Outros modos de
  login serao analisados no futuro, em issues proprias desta spec.
- Login obrigatorio tambem em dev.
- Sem isolamento por usuario (issue #200): todo usuario autenticado ve todos os dados.
- Testes de views usam `core.testing.AuthenticatedTestCase` (client ja autenticado).
- Follow-ups: forms HTML que postam em endpoints JSON (previsoes e revisao de imports)
  exibem 401 cru com sessao expirada; limite de tentativas de login.

## Decisoes da Issue #200

- O app e **single-user formal**, garantido em codigo; nao ha `owner`/`workspace`,
  migration nem backfill. O isolamento por usuario (IDOR entre usuarios) deixa de ser
  explotavel porque nao existe segundo principal.
- Invariante: exatamente um usuario ativo. `core.auth.SingleUserBackend` so autentica
  nessa condicao (fail-closed, inclusive no `/admin/`); com mais de um ativo, ninguem
  entra. Um `pre_save` em `User` (`enforce_single_active_user`) impede criar ou ativar
  um segundo usuario ativo, inclusive via `createsuperuser`. Sem variavel de ambiente
  nova e sem checagem por request.
- Bancos que ja tenham mais de um usuario ativo precisam desativar ou remover os extras
  antes de logar.
- Objeto inexistente responde 404; views `@api_login_required` respondem 404 em JSON
  (via `process_exception` do middleware), views HTML mantem o 404 padrao.
- Gatilho para multiusuario: necessidade real de um segundo usuario; exige nova spec de
  ownership (ver [Escopo do aplicativo](https://lucasdevlop94-1792776715909.atlassian.net/wiki/spaces/FIN/pages/1474561), Confluence). A open question sobre owner para dados
  existentes passa para essa spec.
- Follow-up: lookup de `Recurrence` por nome nao unico (issue #206).

## Task Breakdown Inicial

- [x] Task: Criar settings dev/prod (issue #201).
  - Acceptance: producao nao usa `DEBUG=True` nem `SECRET_KEY` fallback.
  - Verify: `python manage.py check --deploy` com settings de producao.
  - Files: `project/settings.py` ou pacote `project/settings/`.
- [x] Task: Adicionar autenticacao basica (issue #199).
  - Acceptance: views financeiras sensiveis exigem login.
  - Verify: testes de acesso anonimo/autenticado.
  - Files: views/urls afetadas, `templates/registration/`, testes.
- [x] Task: Documentar decisao single-user vs multiusuario (issue #200).
  - Acceptance: scope deixa claro o limite atual e o gatilho para nova spec.
  - Verify: revisao manual.
  - Files: [Escopo do aplicativo](https://lucasdevlop94-1792776715909.atlassian.net/wiki/spaces/FIN/pages/1474561) (Confluence), esta spec.
