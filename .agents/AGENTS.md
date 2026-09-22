# AGENTS.md
#
# Este arquivo roteia os agentes do repositório e define quando usar cada um.
# Baseado no `.agents/project-manifest.yaml` (fonte canônica de contexto).
#
# Regra geral:
# - Ações do repositório seguem as regras de `.github/`.
# - Em caso de conflito, `.github/` prevalece sobre qualquer instrução informal.
# - Não incluir segredos, credenciais ou tokens em exemplos/outputs.

# ============================================================
# PROTOCOLO DE ENTREGA (Delivery Suite)
# ============================================================
# O projeto adota o protocolo de 4 skills independentes:
#   1. task-review   → Validação de escopo, descoberta de stack, Execution Plan
#   2. execute-issue → Implementação guiada por plano + seleção dinâmica de skills
#   3. draft-pr      → Auditoria final: plano vs execução, diff real, homologação
#   4. close-delivery → Limpeza, merge verification, worktree cleanup
#
# Skills localizadas em: `.agents/delivery-suite/skills/`
# Contratos (JSON Schema): `.agents/delivery-suite/contracts/`
# Capabilities padrão: `.agents/delivery-suite/shared/default-capabilities.yaml`

# ============================================================
# AGENTES CORE DO PROTOCOLO (Papéis Principais)
# ============================================================

## task-reviewer (Task Reviewer)
# Path: `.agents/delivery-suite/skills/task-review/SKILL.md`
# Quando usar:
# - Revisar issues executáveis antes da implementação
# - Executar descoberta de stack observada vs declarada (prevenção de manifest_drift)
# - Validar specs aplicáveis e localização real (prevenção de spec_path_drift)
# - Rodar brainstorming + grill-me quando escopo vago
# - Produzir Execution Plan com:
#     * Classificação da issue (feat/fix/refactor/docs/spec/chore)
#     * Decisão de spec (required/recommended/deferred/not_needed)
#     * Matriz de skills recomendadas para o Implementador
#     * Riscos, desvios materiais e critérios de aceite
# - Exigir aprovação humana do plano antes de seguir
#
# Skills associadas:
# - `.agents/delivery-suite/skills/task-review/SKILL.md`
# - `.agents/brainstorming/SKILL.md`
# - `.agents/grill-me/SKILL.md`
# - `.agents/spec-driven-development/SKILL.md`
# Referências:
# - `.agents/delivery-suite/skills/task-review/references/review-protocol.md`
# - `.agents/delivery-suite/skills/task-review/references/project-manifest.schema.json`
# - `.agents/delivery-suite/skills/task-review/references/output-contract.md`

## issue-executor (Issue Executor / Implementer)
# Path: `.agents/delivery-suite/skills/execute-issue/SKILL.md`
# Quando usar:
# - Implementar a issue seguindo o Execution Plan aprovado pelo Task Reviewer
# - Selecionar dinamicamente a combinação de skills baseada no tipo de entrega:
#
#   TIPO DE ENTREGA          | SKILLS COMBINADAS (exemplos)
#   -------------------------|--------------------------------------------------------
#   Documental / Arquitetura | documentation-writer + mermaid-diagrams/excalidraw + create-readme
#   Backend / Django         | tdd + spec-driven-development + controle-financeiro-python-django
#   Automação n8n            | n8n-workflow-patterns + n8n-node-configuration + n8n-code-js/py
#   Diagramas                | mermaid-diagrams / excalidraw-diagram-generator
#   Governança / PR          | controle-financeiro-code-review + pattern-assistant(github)
#   UI / Frontend            | frontend-design + tdd
#
# - Seguir TDD rigoroso (Red-Green-Refactor) para mudanças comportamentais
# - Registrar desvios locais (record_and_continue) vs materiais (pause_and_re_review)
# - Produzir evidências de execução (execution-evidence.json)
#
# Skills associadas:
# - `.agents/delivery-suite/skills/execute-issue/SKILL.md`
# - `.agents/tdd/SKILL.md`
# - `.agents/spec-driven-development/SKILL.md`
# - `.agents/controle-financeiro-python-django/SKILL.md`
# - `.agents/controle-financeiro-code-review/SKILL.md`
# - `.agents/github/skills/documentation-writer/SKILL.md`
# - `.agents/github/skills/create-readme/SKILL.md`
# - `.agents/mermaid/skills/mermaid-diagrams/SKILL.md`
# - `.agents/excalidraw/skills/excalidraw-diagram-generator/SKILL.md`
# - `.agents/n8n/skills/n8n-workflow-patterns/SKILL.md`
# - `.agents/frontend-design/SKILL.md`
# Referências:
# - `.agents/delivery-suite/skills/execute-issue/references/execution-protocol.md`
# - `.agents/delivery-suite/skills/execute-issue/references/capability-resolution.md`
# - `.agents/delivery-suite/skills/execute-issue/references/deviation-policy.md`

## pr-reviewer (PR Reviewer / Draft PR Auditor)
# Path: `.agents/delivery-suite/skills/draft-pr/SKILL.md`
# Quando usar:
# - Auditoria final do PR (draft-pr) antes de aprovar merge
# - Verificar plano vs execução (audit_plan_vs_execution: true)
# - Inspecionar diff real (inspect_real_diff: true)
# - Permitir correções locais seguras (allow_local_safe_fixes: true)
# - Validar critérios de aceite, homologação manual, checklist PR
# - Retornar para execução se achados materiais (material_findings_return_to_execution: true)
# - Preparar fechamento da entrega (close-delivery): branch cleanup, merge verification
#
# Skills associadas:
# - `.agents/delivery-suite/skills/draft-pr/SKILL.md`
# - `.agents/delivery-suite/skills/close-delivery/SKILL.md`
# - `.agents/controle-financeiro-code-review/SKILL.md`
# - `.agents/github/AGENT.md` (pattern-assistant)
# Referências:
# - `.agents/delivery-suite/skills/draft-pr/references/audit-protocol.md`
# - `.agents/delivery-suite/skills/draft-pr/references/finding-policy.md`
# - `.agents/delivery-suite/skills/close-delivery/references/merge-verification.md`

# ============================================================
# AGENTES ESPECIALIZADOS POR DOMÍNIO (Skills de Apoio)
# ============================================================

### pattern-assistant (github)
# Path: `.agents/github/AGENT.md`
# Quando usar:
# - Validar padrão de branch, issue e PR
# - Gerar descrição de PR no template oficial
# - Revisar conformidade de governança antes de merge
# Skills associadas:
# - `.agents/github/skills/create-readme/SKILL.md`
# - `.agents/github/skills/documentation-writer/SKILL.md`
# Exemplos:
# - `.agents/github/examples/input.md`
# - `.agents/github/examples/output.md`

### n8n-automation-architect (n8n)
# Path: `.agents/n8n/AGENT.md`
# Quando usar:
# - Desenhar arquitetura de workflows n8n (webhook, API, banco, AI, agendado, batch)
# - Configurar nodes com campos obrigatórios e dependências por operação
# - Escrever/validar expressões `{{ }}` e mapeamentos entre nodes
# - Implementar lógica em Code node (JavaScript ou Python quando necessário)
# - Validar e preparar workflows para ativação com risco e rollback
# Skills associadas:
# - `.agents/n8n/skills/n8n-workflow-patterns/SKILL.md`
# - `.agents/n8n/skills/n8n-node-configuration/SKILL.md`
# - `.agents/n8n/skills/n8n-expression-syntax/SKILL.md`
# - `.agents/n8n/skills/n8n-code-javascript/SKILL.md`
# - `.agents/n8n/skills/n8n-code-python/SKILL.md`
# - `.agents/n8n/skills/n8n-mcp-tools-expert/SKILL.md`

### excalidraw-diagram-assistant (excalidraw)
# Path: `.agents/excalidraw/AGENT.md`
# Quando usar:
# - Converter descrição textual em diagramas `.excalidraw`
# - Criar flowchart, arquitetura, relacionamento, mind map, DFD, swimlane, class, sequence e ER
# - Estruturar layout visual legível com conexões e hierarquia claras
# - Garantir JSON compatível com schema do Excalidraw
# Skills associadas:
# - `.agents/excalidraw/skills/excalidraw-diagram-generator/SKILL.md`

### mermaid-diagram-assistant (mermaid)
# Path: `.agents/mermaid/AGENT.md`
# Quando usar:
# - Converter descrição textual em diagramas Mermaid em Markdown
# - Criar flowchart, sequence, class, ER, state, gantt e C4
# - Melhorar legibilidade visual e padronizar estilo de diagramas Mermaid existentes
# - Revisar sintaxe Mermaid para compatibilidade de renderização
# Skills associadas:
# - `.agents/mermaid/skills/mermaid-diagrams/SKILL.md`
# - `.agents/mermaid/skills/pretty-mermaid/SKILL.md`

### django-developer (Django Financeiro)
# Path: `.agents/controle-financeiro-python-django/SKILL.md` (orientado por Skills)
# Quando usar:
# - Implementar features no projeto Controle Financeiro (models, views, forms, templates)
# - Revisar código, PRs, diffs e regras de negócio com foco financeiro e na arquitetura Django local
# Skills associadas:
# - `.agents/controle-financeiro-python-django/SKILL.md`
# - `.agents/controle-financeiro-code-review/SKILL.md`

### software-engineer-workflow (Global / Fundamentos)
# Path: Skills globais (`.agents/*/SKILL.md`)
# Quando usar:
# - Levantar requisitos e explorar intenção do usuário (`brainstorming`)
# - Refinar e estressar o design e plano arquitetural (`grill-me`)
# - Criar especificações de software antes do código (`spec-driven-development`)
# - Desenvolver testes orientados a comportamento (red-green-refactor) (`tdd`)
# - Adotar direção estética opinativa e design visual autêntico para UIs (`frontend-design`)
# Skills associadas:
# - `.agents/brainstorming/SKILL.md`
# - `.agents/grill-me/SKILL.md`
# - `.agents/spec-driven-development/SKILL.md`
# - `.agents/tdd/SKILL.md`
# - `.agents/frontend-design/SKILL.md`

# ============================================================
# FLUXOS RECOMENDADOS (Git-flow + Delivery Suite)
# ============================================================

## Fluxo Principal: Issue → Branch → Task Review → Execução → Draft PR → Close

1. **Abrir Issue** no template correto em `.github/ISSUE_TEMPLATE/` (feat, fix, tech-debt, ux-ui, bug).
2. **Criar Branch** seguindo convenção (ex.: `feat/123-nova-funcionalidade`).
3. **Task Reviewer** (`task-review`):
   - Executa descoberta de stack (observada vs declarada via `project-manifest.yaml`)
   - Localiza PRD/spec aplicável (caminho real, registra drift se divergir)
   - Se escopo vago → `brainstorming` + `grill-me`
   - Produz **Execution Plan** com matriz de skills recomendadas
   - **Exige aprovação humana** do plano
4. **Issue Executor** (`execute-issue`):
   - Recebe Execution Plan aprovado
   - Seleciona combinação de skills conforme tipo de entrega (tabela acima)
   - Implementa com TDD (se comportamental) ou skills documentais/diagramação
   - Registra desvios locais vs materiais
   - Gera `execution-evidence.json`
5. **Abrir Draft PR** seguindo `.github/PULL_REQUEST_TEMPLATE.md` com `Closes #<numero>`.
6. **PR Reviewer** (`draft-pr` + `close-delivery`):
   - Auditoria: plano vs execução, diff real, critérios de aceite
   - Homologação manual (roteiro no PR template)
   - Se achados materiais → retorna para execução
   - Aprova → merge (squash), cleanup branch/worktree

## Fluxo Específico: Django / Core Development
1. Task Reviewer valida spec aplicável (`docs/specs/XXX-*.md`) ou exige criação.
2. Issue Executor usa: `tdd` + `spec-driven-development` + `controle-financeiro-python-django`.
3. Antes de PR: auto-code-review com `controle-financeiro-code-review`.
4. PR Reviewer valida: migrações, testes, Decimal, regras de negócio em services/selectors.

## Fluxo Específico: Documentação / Arquitetura
1. Task Reviewer identifica tipo `docs` ou `spec`.
2. Issue Executor usa: `documentation-writer` + `mermaid-diagrams` OU `excalidraw-diagram-generator` + `create-readme`.
3. PR Reviewer valida: renderização, links, rastreabilidade para issue/spec.

## Fluxo Específico: Automação n8n
1. Task Reviewer valida objetivo, trigger, sistemas envolvidos.
2. Issue Executor usa: `n8n-workflow-patterns` + `n8n-node-configuration` + `n8n-code-*`.
3. PR Reviewer valida: risco, rollback, campos obrigatórios, expressões.

## Fluxo Específico: GitHub / Governança
1. `pattern-assistant` valida branch, issue, PR template.
2. `documentation-writer` + `create-readme` para docs de governança.

# ============================================================
# EXPANSÃO FUTURA
# ============================================================
# Para adicionar novo agente/skill:
# 1. Criar pasta `.agents/<stack>/` ou `.agents/delivery-suite/skills/<nova-skill>/`
# 2. Adicionar `SKILL.md` (e `AGENT.md` se agente fino)
# 3. Registrar no `project-manifest.yaml` em `capabilities.custom` ou `agents`
# 4. Atualizar este `AGENTS.md` (path, uso, skills, exemplos)
# 5. Seguir build order do delivery-suite se for skill do protocolo

# ============================================================
# ARQUIVOS DE REFERÊNCIA CANÔNICA
# ============================================================
# - Project Manifest: `.agents/project-manifest.yaml`
# - Branching Rules: `.github/BRANCHING.md` (a criar) / inferido do CI
# - PR Template: `.github/PULL_REQUEST_TEMPLATE.md`
# - CI Pipeline: `.github/workflows/ci.yml`
# - Issue Templates: `.github/ISSUE_TEMPLATE/*.yml`
# - Delivery Suite Contracts: `.agents/delivery-suite/contracts/*.json`
# - Delivery Suite Skills: `.agents/delivery-suite/skills/*/SKILL.md`