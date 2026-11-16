# Design — remodelação da interface (FIN-34)

Planejamento visual da remodelação: tema claro inspirado na Wise e tema escuro
inspirado na Mercury. A implementação no CSS e nos templates é da Etapa 3, junto
com a responsividade (#240 a #242).

## Conteúdo

| Caminho | O que é |
|---|---|
| `DESIGN.md` | Tokens, tipografia e componentes finais dos dois temas (fonte para a Etapa 3) |
| [Figma](https://www.figma.com/design/ZXFAOIcnPMhKz8AwLhY7Oe) | Variáveis, componentes e telas (8 de celular e 4 de desktop, claro e escuro) |
| `reference/wise.DESIGN.md` | DESIGN.md da Wise, cópia sem alteração do pacote `getdesign@0.6.26` (VoltAgent/awesome-design-md, MIT) |
| `reference/mercury.DESIGN.md` | DESIGN.md da Mercury, mesma origem |
| `wireframes/fin-34-wireframes-celular.excalidraw` | Rascunho de estrutura no celular (360px): 12 telas, navegação e variantes de tabela da ADR-014 |
| `wireframes/fin-34-wireframes-desktop.excalidraw` | Rascunho de estrutura no desktop (1280px): início, lançamentos, revisão de importações e relatório |
| `wireframes/*.png` | Prévia estática dos dois arquivos acima |
| `tokens.md` | Semântica de status e variantes do componente `.status`; aponta para o `DESIGN.md` (a prévia `ui-preview-home.html` foi removida na 3.1) |

Os arquivos `reference/` são material de consulta, não regra ativa: os tokens do
app saem das decisões abaixo. Os wireframes abrem em https://excalidraw.com
(Abrir → arquivo `.excalidraw`).

## Decisões de 14/11/2026

- **Fundo do tema claro:** sage `#e8ebe6` com cards brancos; a separação vem do
  contraste de superfície, sem borda nem sombra.
- **Cor de ação:** verde-lima `#9fe870` nos dois temas, com texto `#0e0f0c`.
  O índigo da Mercury não entra.
- **Tipografia:** Inter nos dois temas. Texto e interface iguais (400/600);
  só saldo e títulos mudam de peso (800–900 no claro, 480 no escuro).
- **Receita e despesa:** valores em `#054d28` / `#d03238` no claro, menta e
  salmão com contraste AA no escuro; fundos em `#e2f6d5` e rosa claro derivado.
  Texto secundário `#454745` no lugar de `#868685`, que reprova AA.
- **Formas e espaço:** escala da Wise nos dois temas (raios 8/12/16/24/pílula,
  espaçamento base 4px).

- **Navegação no celular:** barra inferior com Início, Lançamentos, novo
  lançamento, Faturas e Mais; as demais telas e a troca de tema ficam na folha
  "Mais". No desktop, sidebar clara e agrupada.
- **Tabelas no celular:** lista empilhada (descrição e valor na primeira linha,
  metadados na segunda); tabelas-resumo do relatório viram linhas rótulo e
  valor. Registrado na ADR-014 (Confluence, espaço FIN).
- **Ajustes de estrutura:** "Dashboard" passa a se chamar "Relatório"; no início
  do celular, Realizado/Pendente/Previsto viram um seletor sobre um único card
  de saldo; a barra de ações em lote da revisão de importações fica em uma linha.

## Pendente

- Telas só em wireframe, sem versão no Figma: detalhe do lançamento, importar
  extrato, lista de faturas e folha "Mais".
