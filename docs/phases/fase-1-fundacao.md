# Fase 1 - Fundacao (Django, Docker e CI)

## Objetivo da fase

Estabelecer a base tecnica do projeto para desenvolvimento local, execucao padronizada e validacao automatizada.

Referencias:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## O que foi criado

### 1. Projeto Django

Arquivos e estrutura inicial do projeto:

- `manage.py`
- `project/settings.py`
- `project/urls.py`
- `project/asgi.py`
- `project/wsgi.py`

Resultado:

- Projeto Django funcional para evolucao das proximas fases.

### 2. App `core`

Arquivos principais:

- `core/apps.py`
- `core/views.py`
- `core/urls.py`
- `core/tests/test_health_check.py`

Papel do app:

- Concentrar funcionalidades base e compartilhadas do sistema.
- Expor endpoint simples de health check para validacao da aplicacao.

### 3. Docker e Docker Compose

Arquivos:

- `DOCKERFILE`
- `docker-compose.yml`

Como funciona no projeto:

- O container instala dependencias de `requirements.txt`.
- O servico `web` executa migrations e sobe o servidor Django.
- Porta publicada: `8001` (host) -> `8000` (container).
- Volume montado para desenvolvimento local com codigo sincronizado.

Comando principal:

```bash
docker compose up --build
```

### 4. GitHub Actions (CI)

Arquivo:

- `.github/workflows/ci.yml`

Objetivo no fluxo:

- Validar automaticamente o projeto a cada push/PR.
- Garantir que instalacao de dependencias e testes continuem funcionando.

## Testes implementados na fase

### Health check

Arquivo:

- `core/tests/test_health_check.py`

Cobertura atual:

- Verifica resposta HTTP 200 do endpoint de health check.
- Verifica conteudo esperado da resposta (`OK`).

Execucao local:

```bash
python3 manage.py test
```

## Status da fase

Fase 1 concluida conforme base tecnica prevista no plano.
