# Política de Branching (Branching Model)

Este documento define as regras canônicas de criação, nomenclatura e ciclo de vida das branches no repositório `controle-financeiro`. 

## 1. Branch Base

Todas as novas branches devem ser criadas a partir da branch principal do projeto:
- **`main`**: Branch de integração contínua e fonte da verdade para o ambiente de produção. Sempre reflete o código testado e homologado.

## 2. Padrões de Nomenclatura (Prefixos)

A nomenclatura da branch deve indicar claramente o tipo de trabalho sendo realizado e referenciar a issue associada (se houver).

| Prefixo | Uso | Exemplo |
| --- | --- | --- |
| `feat/` | Novas funcionalidades, comportamentos ou capacidades. | `feat/12-autenticacao-jwt` |
| `fix/` | Correções de bugs ou falhas de comportamento em produção. | `fix/34-calculo-cdi` |
| `refactor/` | Melhorias técnicas, organização de código ou dívida técnica (sem mudança comportamental). | `refactor/111-reorganizar-agentes` |
| `chore/` | Ajustes de infraestrutura, CI/CD, dependências, scripts ou migrações isoladas. | `chore/update-pytest-version` |
| `docs/` | Atualizações exclusivas de documentação, Readme ou tutoriais. | `docs/222-atualizar-readme` |
| `spec/` | Criação ou alteração de especificações (PRD, contratos, arquitetura). | `spec/55-novo-contrato-api` |
| `ui/` / `ux/` | Alterações puramente visuais, design system ou acessibilidade. | `ui/44-ajustar-cores-botoes` |

**Regra de Ouro**: O nome da branch deve ser em letras minúsculas (kebab-case), sem acentos ou caracteres especiais, e preferencialmente incluir o número da issue associada.

## 3. Fluxo de Vida da Branch

1. **Criação**: `git checkout -b <prefixo>/<numero-issue>-<descricao-curta> main`
2. **Trabalho local**: Commits frequentes, uso de TDD (quando aplicável) e integração contínua (rodar `python manage.py test` localmente).
3. **Sincronização**: `git pull --rebase origin main` para manter a branch atualizada com a base.
4. **Draft PR**: Abertura de Pull Request no modo Draft para auditoria e homologação (`draft-pr`).
5. **Merge**: Após aprovação (Review) e passagem no CI (GitHub Actions), o merge deve ser feito via **Squash and Merge** para manter o histórico da `main` limpo.
6. **Limpeza**: A branch local e remota deve ser deletada após o merge (`close-delivery`).

## 4. Worktrees (Opcional, porém Recomendado)

Para evitar interferências entre branches ou quando o trabalho exige `database_migration` ou `multi_subsystem`, o uso de Git Worktrees é recomendado.

- Diretório padrão: `../worktrees/`
- Exemplo de criação: `git worktree add ../worktrees/feat-123-autenticacao feat/123-autenticacao-jwt`

## 5. Regras Gerais

- **Nenhum commit direto na `main`**. Todas as alterações devem passar por Pull Request.
- **Toda Issue Executável exige uma branch própria**. (Conforme `executable_issue_requires_branch: true` no manifesto).
- **Sem Branches Órfãs**: Branches inativas por mais de 14 dias sem PR devem ser arquivadas ou deletadas.