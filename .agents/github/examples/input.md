# Exemplo de input - pattern-assistant

## Contexto
- Repositorio: `n8n-workflows`
- Branch atual: `chore/repo-agents-skills`
- Issue: `numero da issue` (technical task)
- Objetivo: padronizar arquitetura de agentes e skills

## Mudancas realizadas
- Reorganizacao da estrutura para `.agents/<stack>/skills`
- Criacao de `.agents/github/AGENT.md`
- Inclusao de skills:
  - `create-readme`
  - `documentation-writer`

## Arquivos alterados
- `.agents/github/AGENT.md`
- `.agents/github/skills/create-readme/SKILL.md`
- `.agents/github/skills/documentation-writer/SKILL.md`
- `.gitignore`

## Pedido ao agente
1. Validar conformidade com:
   - `.github/BRANCHING.md`
   - `.github/pull_request_template.md`
   - `.github/ISSUE_TEMPLATE/*`
2. Sinalizar gaps de governanca.
3. Gerar descricao de PR em markdown pronta para colar.
