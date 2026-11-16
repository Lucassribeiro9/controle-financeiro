# Design Tokens - Controle Financeiro

Os tokens de cor, tipografia, forma e espaço, nos temas claro e escuro, estão em
[`DESIGN.md`](DESIGN.md) e são implementados em `static/css/tokens.css`
(`color/bg/canvas` vira `--color-bg-canvas`). Este arquivo guarda só o que o
`DESIGN.md` não cobre: a semântica de status e as regras de formatação.

Os testes de `core/tests/test_static_css.py` leem a tabela de cores do `DESIGN.md` e
conferem `tokens.css` nos dois temas; mudar uma cor é mudar as duas fontes juntas.

## 1. Status

O mapeamento entre o status do banco e a variante visual vive em
`STATUS_BADGE_VARIANTS`, em `core/templatetags/money.py`; o filtro `status_badge_class`
devolve `status status--<variante>` (componente `.status` de `components.css`).
`active_badge_class` usa `positive` para ativo e `neutral` para inativo.

| Variante | Significado | Status |
| :--- | :--- | :--- |
| `positive` | Concluído, saudável | `active`, `achieved`, `approved`, `confirmed`, `completed`, `paid` |
| `warning` | Atenção, pendente, parcial | `pending`, `partially_paid`, `partial`, `duplicate` |
| `negative` | Erro, risco, atrasado | `late`, `missed`, `at_risk` |
| `neutral` | Previsto, aberto, inativo, cancelado, ignorado | `open`, `forecasted`, `forecast`, `on_track`, `canceled`, `cancelled`, `discarded`, `ignored`, `inactive`, `silenced` |

Status sem entrada na tabela caem em `neutral`. As antigas variantes `info` (azul)
e `neutral` colapsaram em Neutro (spec 017, D6).

## 2. Formatação de dados

### Valores monetários
- **Moeda:** Real (R$) ou Dólar (US$) conforme a conta.
- **Separadores:** padrão pt-BR (ponto para milhar, vírgula para decimal).
- **Precisão:** 2 casas decimais para valores transacionais.

### Percentuais
- **Participação/share:** número inteiro sem decimal (ex.: "32%").
- **Taxas:** mantêm decimais quando a precisão importa (ex.: "11,25% a.a.").

### Datas e períodos
- **Datas curtas:** `DD/MM/AAAA`.
- **Período legível:** `Nome do Mês/AAAA` (ex.: "Maio/2026") em títulos.
- **Numérico compacto:** `M/AAAA` só em filtros e controles compactos.

## 3. Breakpoint e componentes

- Breakpoint principal: `768px`. Abaixo dele, listas viram lista empilhada (ADR-014) e
  filtros ficam recolhidos.
- Partials compartilhados em `templates/partials/`: `status_badge.html`,
  `empty_state.html`, `filter_bar.html` e `messages.html`, sobre as classes de
  `static/css/components.css`.
- Tokens do gráfico (`--chart-income`, `--chart-expense`, `--chart-balance`,
  `--chart-grid`, `--chart-text`, `--chart-surface`) são lidos por `static/js/dashboard.js`.
