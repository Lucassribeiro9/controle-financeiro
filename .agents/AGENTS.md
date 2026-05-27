# AGENTS.md

Este arquivo roteia os agentes do repositorio e define quando usar cada um.

## Regra geral
- Referente as acoes do repositorio, sempre priorizar as regras de `.github/`.
- Em caso de conflito, `.github/` prevalece sobre qualquer instrucao informal.
- Nao incluir segredos, credenciais ou tokens em exemplos/outputs.

## Agentes disponiveis

### pattern-assistant (github)
- Path: `.agents/github/AGENT.md`
- Quando usar:
  - Validar padrao de branch, issue e PR
  - Gerar descricao de PR no template oficial
  - Revisar conformidade de governanca antes de merge
- Skills associadas:
  - `.agents/github/skills/create-readme/SKILL.md`
  - `.agents/github/skills/documentation-writer/SKILL.md`
- Exemplos:
  - `.agents/github/examples/input.md`
  - `.agents/github/examples/output.md`

### n8n-automation-architect (n8n)
- Path: `.agents/n8n/AGENT.md`
- Quando usar:
  - Desenhar arquitetura de workflows n8n (webhook, API, banco, AI, agendado, batch)
  - Configurar nodes com campos obrigatorios e dependencias por operacao
  - Escrever/validar expressoes `{{ }}` e mapeamentos entre nodes
  - Implementar logica em Code node (JavaScript ou Python quando necessario)
  - Validar e preparar workflows para ativacao com risco e rollback
- Skills associadas:
  - `.agents/n8n/skills/n8n-workflow-patterns/SKILL.md`
  - `.agents/n8n/skills/n8n-node-configuration/SKILL.md`
  - `.agents/n8n/skills/n8n-expression-syntax/SKILL.md`
  - `.agents/n8n/skills/n8n-code-javascript/SKILL.md`
  - `.agents/n8n/skills/n8n-code-python/SKILL.md`
  - `.agents/n8n/skills/n8n-mcp-tools-expert/SKILL.md`

### excalidraw-diagram-assistant (excalidraw)
- Path: `.agents/excalidraw/AGENT.md`
- Quando usar:
  - Converter descricao textual em diagramas `.excalidraw`
  - Criar flowchart, arquitetura, relacionamento, mind map, DFD, swimlane, class, sequence e ER
  - Estruturar layout visual legivel com conexoes e hierarquia claras
  - Garantir JSON compativel com schema do Excalidraw
- Skills associadas:
  - `.agents/excalidraw/skills/excalidraw-diagram-generator/SKILL.md`

### mermaid-diagram-assistant (mermaid)
- Path: `.agents/mermaid/AGENT.md`
- Quando usar:
  - Converter descricao textual em diagramas Mermaid em Markdown
  - Criar flowchart, sequence, class, ER, state, gantt e C4
  - Melhorar legibilidade visual e padronizar estilo de diagramas Mermaid existentes
  - Revisar sintaxe Mermaid para compatibilidade de renderizacao
- Skills associadas:
  - `.agents/mermaid/skills/mermaid-diagrams/SKILL.md`
  - `.agents/mermaid/skills/pretty-mermaid/SKILL.md`

## Fluxo recomendado (github)
1. Abrir issue no template correto em `.github/ISSUE_TEMPLATE/`.
2. Criar branch conforme `.github/BRANCHING.md`.
3. Usar o agente adequado para validar padroes e preparar PR.
4. Abrir PR seguindo `.github/pull_request_template.md` com `Closes #<numero>`.
5. Quando gerar descricao de PR, usar como referencia de formato o exemplo em `.agents/github/examples/output.md`.

## Fluxo recomendado (n8n)
1. Definir objetivo da automacao, trigger e sistemas envolvidos.
2. Escolher o padrao de workflow com base em `.agents/n8n/skills/n8n-workflow-patterns/SKILL.md`.
3. Configurar nodes e expressoes, validando campos obrigatorios e dependencias por operacao.
4. Validar nodes/workflow antes da ativacao e registrar risco principal com rollback.
5. Ativar workflow e monitorar as primeiras execucoes em ambiente controlado.

## Fluxo recomendado (excalidraw)
1. Definir objetivo do diagrama, publico-alvo e nivel de detalhe.
2. Classificar o tipo de diagrama (flowchart, arquitetura, relacionamento, mind map, etc.).
3. Extrair entidades/etapas/relacoes e gerar arquivo `.excalidraw` com estrutura valida.
4. Revisar legibilidade (layout, espacamento, setas e rotulos) e ajustar suposicoes necessarias.
5. Entregar diagrama final pronto para abrir e editar no Excalidraw.

## Fluxo recomendado (mermaid)
1. Definir objetivo do diagrama, publico-alvo e contexto de uso (README, docs, PR, runbook).
2. Classificar o tipo de diagrama Mermaid mais adequado (flowchart, sequence, class, ER, state, gantt, C4).
3. Extrair entidades/etapas/relacoes e gerar bloco Mermaid com sintaxe valida.
4. Revisar legibilidade (direcao do fluxo, nomenclatura, agrupamento e estilos).
5. Validar renderizacao no ambiente alvo e registrar suposicoes adotadas.

## Expansao futura
Para adicionar novo agente:
1. Criar pasta `.agents/<stack>/`
2. Adicionar `.agents/<stack>/AGENT.md`
3. Adicionar skills em `.agents/<stack>/skills/`
4. Registrar aqui em `AGENTS.md` (path, uso, skills, exemplos)
