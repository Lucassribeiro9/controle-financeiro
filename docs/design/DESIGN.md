# DESIGN.md — controle-financeiro

Tokens e componentes da remodelação (FIN-34). Tema claro inspirado na Wise, tema
escuro inspirado na Mercury. Fonte visual: arquivo Figma
[controle-financeiro · Remodelação (FIN-34)](https://www.figma.com/design/ZXFAOIcnPMhKz8AwLhY7Oe).
Referências originais em `reference/`. Implementação no CSS: Etapa 3.

## Cores

Os nomes viram variáveis CSS trocando `/` por `-` (ex.: `color/bg/canvas` →
`--color-bg-canvas`). No Figma ficam em duas coleções com os mesmos nomes,
"Tema claro" e "Tema escuro" (o plano Starter só permite um modo por coleção).

| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `color/bg/canvas` | `#e8ebe6` | `#171721` | Fundo da página |
| `color/bg/surface` | `#ffffff` | `#1e1e2a` | Cards, sidebar, barra inferior, campos |
| `color/bg/surface-muted` | `#f3f5f1` | `#272736` | Trilho de progresso, status neutro |
| `color/bg/brand-pale` | `#e2f6d5` | `#283829` | Item ativo da navegação |
| `color/text/primary` | `#0e0f0c` | `#ededf3` | Texto principal |
| `color/text/secondary` | `#454745` | `#c3c3cc` | Legendas e metadados |
| `color/text/on-primary` | `#0e0f0c` | `#0e0f0c` | Texto sobre o verde-lima |
| `color/border/default` | `#d5d9d2` | `#34344a` | Divisórias de lista e tabela |
| `color/border/strong` | `#0e0f0c` | `#70707d` | Borda de campo e botão terciário |
| `color/action/primary` | `#9fe870` | `#9fe870` | Botão principal (uma cor de ação nos dois temas) |
| `color/action/secondary` | `#dde2d9` | `#3b3c4b` | Botão secundário, seletor de período |
| `color/money/income` | `#054d28` | `#7ee0a8` | Valor de receita |
| `color/money/income-bg` | `#e2f6d5` | `#1f3a2d` | Fundo de receita, status positivo |
| `color/money/expense` | `#d03238` | `#ff8f85` | Valor de despesa sobre superfície |
| `color/money/expense-strong` | `#a72027` | `#ff8f85` | Texto de despesa sobre o fundo rosa |
| `color/money/expense-bg` | `#fde8e8` | `#3d2229` | Fundo de despesa, status negativo |
| `color/status/warning-bg` | `#fff4cc` | `#3a3220` | Alertas, status de atenção |
| `color/status/warning-text` | `#4a3b1c` | `#ffd97a` | Texto sobre alerta |

Todas as combinações de texto acima passam AA (4,5:1) no fundo em que são usadas.
Exceção a evitar: `color/money/expense` claro direto sobre `color/bg/canvas` dá
4,16:1; valores de despesa ficam sempre dentro de um card (`surface`, 5,01:1).

## Tipografia

Inter nos dois temas. Só saldo e título mudam de peso entre os temas.

| Estilo | Claro | Escuro | Tamanho / linha |
|---|---|---|---|
| Saldo | Extra Bold (800) | Medium (500) | 40 / 44 |
| Título | Extra Bold (800) | Medium (500) | 26 / 32 |
| Seção | Semi Bold | Semi Bold | 17 / 24 |
| Corpo | Regular | Regular | 15 / 22 |
| Corpo forte, Valor, Botão | Semi Bold | Semi Bold | 15 / 20–22 |
| Legenda | Regular | Regular | 12 / 16 |

## Forma e espaço

- Raios: `radius/sm` 8, `md` 12 (campos), `lg` 16 (alertas), `xl` 24 (cards e
  botões), `pill` 9999 (status, seletores).
- Espaçamento base 4px: `space/xs` 4, `sm` 8, `md` 12, `lg` 16, `xl` 24, `2xl` 32, `3xl` 48.
- Elevação por contraste de superfície: card `surface` sobre `canvas`, sem sombra.

## Componentes (Figma, página "Tokens e componentes")

Todos com a variante `Tema=Claro|Escuro`.

| Componente | Variantes / propriedades |
|---|---|
| Botão | `Estilo` Primário, Secundário, Terciário; texto `Rótulo` |
| Status | `Tipo` Positivo, Atenção, Neutro, Negativo; texto `Rótulo` |
| Linha de lançamento | `Tipo` Despesa, Receita; textos `Descrição`, `Detalhe`, `Valor` |
| Card de saldo | textos `Rótulo`, `Saldo`, `Receitas`, `Despesas` |
| Campo | textos `Rótulo`, `Valor` |
| Alerta | textos `Título`, `Detalhe` |
| Topo celular | texto `Período` |
| Barra inferior | Início, Lançamentos, novo lançamento, Faturas, Mais |
| Sidebar desktop | grupos Principal, Dinheiro, Dados; item ativo com `brand-pale` |

## Layout

- Celular (abaixo de 768px): topo com marca e período, conteúdo com margem de
  16px, barra inferior fixa. Listas viram lista empilhada (ADR-014).
- Desktop (768px ou mais): sidebar de 240px, conteúdo com margem de 40px, ação
  principal no canto superior direito, tabelas completas.
