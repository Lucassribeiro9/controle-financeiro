# Design Tokens - Controle Financeiro

Este documento define a linguagem visual e os padrões de interface do projeto, servindo como fonte única de verdade para cores, tipografia, espaçamento e comportamento da UI.

## 1. Cores Semânticas

As cores seguem uma lógica funcional para facilitar a compreensão imediata do estado financeiro ou operacional.

| Variante | Cor (CSS Variable) | Significado | Exemplos de Status |
| :--- | :--- | :--- | :--- |
| **Success** | `--success` | Positivo, concluído, saudável | `paid`, `confirmed`, `completed`, `active` |
| **Warning** | `--warning` | Atenção, pendente, parcial | `pending`, `partial`, `duplicate` |
| **Info** | `--info` | Informativo, previsto, aberto | `forecasted`, `open`, `on_track` |
| **Danger** | `--danger` | Erro, risco, atrasado | `late`, `at_risk`, `missed` |
| **Neutral** | `--neutral` | Inativo, cancelado, ignorado | `canceled`, `ignored`, `inactive`, `silenced` |

### Mapeamento de Status
O mapeamento oficial entre o banco de dados e as classes visuais é definido no filtro `status_badge_class` em `core/templatetags/money.py`.

## 2. Formatação de Dados

A consistência na exibição de valores financeiros e datas é crucial para a legibilidade.

### Valores Monetários
- **Moeda:** Sempre em Real (R$) ou Dólar (US$) dependendo da conta.
- **Separadores:** Padrão pt-BR (ponto para milhar, vírgula para decimal).
- **Precisão:** 2 casas decimais obrigatórias para valores transacionais.

### Percentuais
- **Participação/Share:** Exibido como **número inteiro sem decimal** (ex: "32%") em contextos de gráficos ou resumos de share.
- **Taxas (CDI/Juros):** Mantém decimais conforme a necessidade de precisão (ex: "11,25% a.a.").

### Datas e Períodos
- **Datas curtas:** `DD/MM/AAAA`.
- **Período Legível:** Títulos de seção e dashboards devem usar o formato `Nome do Mês/AAAA` (ex: "Maio/2026").
- **Formato Numérico Compacto:** `M/AAAA` (ex: "5/2026") restrito a controles de filtro e inputs compactos.

## 3. Breakpoints e Responsividade

A interface deve ser operacional e funcional em diferentes tamanhos de tela.

- **Mobile First:** Priorizar a legibilidade em dispositivos menores.
- **Breakpoint Principal:** `768px`.
- **Comportamento de Tabelas:**
    - No Desktop: Tabelas densas com scroll quando necessário.
    - No Mobile (< 768px): Scroll horizontal para tabelas financeiras ou empilhamento de cards em listas específicas.

## 4. Componentes (Partials)

Os componentes reutilizáveis devem ser implementados em `templates/partials/`:

- `empty_state.html`: Usado quando não há dados, deve sempre conter um título, descrição e uma chamada para ação (CTA).
- `status_badge.html`: Renderiza o badge com a cor semântica correta.
- `filter_bar.html`: Barra de filtros com botão "Limpar Filtros".
