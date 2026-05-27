# Exemplo de output - pattern-assistant

## Resultado da validacao

### Conformidades encontradas
- Branch segue o padrao de `chore/<escopo>-<ajuste-curto>`.
- Issue classificada como `technical task`, coerente com o escopo.
- Referencias de governanca estao presentes no `AGENT.md`.
- Skills necessarias para documentacao estao disponiveis em `.agents/github/skills/`.

### Pontos de ajuste
- Garantir que a issue contenha criterios de aceite completos e risco/mitigacao.
- Confirmar que a PR inclua `Closes #<numero da issue>` no corpo.
- Verificar se a estrutura antiga `.agents/skills/...` foi totalmente removida do versionamento.

## Titulo sugerido de PR
`chore(repo): reorganizar arquitetura de agents e skills por stack`

## Descricao sugerida de PR (markdown)
```md
## Titulo sugerido
`chore(repo): reorganizar arquitetura de agents e skills por stack`

## Issue relacionada
`Closes #<numero da issue>`

## Resumo
Esta PR reorganiza a arquitetura de agentes para o padrao `.agents/<stack>/skills`, mantendo as skills do dominio `github` sob uma estrutura mais previsivel e escalavel. Tambem adiciona exemplos de uso do agente para onboarding.

## Tipo de mudanca
- [x] `chore`
- [x] `docs`

## Escopo impactado
- `.agents/github/AGENT.md`
- `.agents/github/skills/create-readme/SKILL.md`
- `.agents/github/skills/documentation-writer/SKILL.md`
- `.agents/github/examples/input.md`
- `.agents/github/examples/output.md`

## Checklist de validacao
- [x] Estrutura por stack aplicada
- [x] Sem segredos versionados
- [x] Evidencias de uso do agente adicionadas
- [x] Diff focado e revisavel

## Riscos e rollback
- Risco principal: baixo (impacto organizacional)
- Rollback: restaurar paths antigos e remover estrutura nova em PR de reversao
```
