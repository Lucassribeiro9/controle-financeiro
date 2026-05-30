# Spec 005 - Cartoes, Faturas e Limites

## Contexto

Cartoes e faturas sao parte central do uso diario. O usuario precisa entender limite usado, limite disponivel, vencimento, status da fatura e impacto do pagamento sem precisar navegar por caminhos indiretos.

## Objetivo

Melhorar dominio e UX de cartoes/faturas, consumir limite de credito ao lancar compra e dar acesso direto as faturas.

## Fora de Escopo

- Integracao bancaria automatica.
- Pagamento real via API bancaria.
- Controle multiusuario.
- Alterar retroativamente todas as faturas antigas sem migracao planejada.

## Estado Atual

O app ja possui cartoes, faturas e pagamentos, mas compras pendentes no credito ainda precisam consumir limite de forma clara. Faturas tambem precisam de acesso direto e visual mais dinamico.

## Comportamento Esperado

- Compra no credito reduz limite disponivel no momento do lancamento.
- Faturas aparecem em menu/rota propria.
- Fatura aberta mostra valor previsto.
- Fatura fechada mostra valor fechado.
- Fatura paga mostra valor pago e conta usada.
- Pagamento parcial altera indicadores de forma clara.

## Telas e Componentes

Telas afetadas:

- lista de cartoes;
- detalhe de cartao;
- lista de faturas;
- detalhe de fatura;
- pagamento de fatura;
- criacao de compra no credito.

Componentes:

- indicador de limite usado;
- indicador de limite disponivel;
- resumo de fatura;
- confirmacao de pagamento;
- badge de status.

## Regras de Negocio

- Limite disponivel e dinamico (calculado em tempo de execucao, nao persistido).
- O calculo do limite disponivel segue o **Modelo do Mercado Real** brasileiro: consome do limite cadastrado o valor **total** de todas as compras ativas (`card_purchase`) vinculadas a faturas que **nao** estao no status `paid` (ou seja, faturas abertas, previstas, fechadas pendentes, atrasadas ou parcialmente pagas).
- Compra pendente no credito consome limite normalmente.
- Cancelamento ou ignorar compra (status da transacao `canceled` ou `ignored`) remove o valor da compra do calculo do limite usado.
- Foco exclusivo em cartoes de `CREDIT`. Cartoes do tipo `benefit`, `transport` ou `prepaid` tem gestao fina de saldos separada e ficam para o backlog.
- Pagamento de fatura exige indicar conta financeira de saida.

## Dados, Services e Selectors

Criar ou evoluir:

- selector de limite usado/disponivel em `cards/selectors.py` com o calculo acumulativo;
- selector de resumo de fatura para a tela de detalhes;
- service de pagamento com contexto de saldo projetado;
- rotas diretas para faturas.

## Estados de Erro

- Pagamento de fatura sem conta financeira valida deve ser bloqueado com mensagem clara.
- Compra no cartao que excede o limite disponivel **nao bloqueia** a criacao da transacao (Alerta Soft), exibindo um alerta visual em destaque na UI para fins de controle pessoal.
- Tentativa de pagar valor maior do que o restante da fatura deve exibir erro de validacao.
- Fatura inexistente ou ja paga deve ter feedback contextual apropriado.

## Testes Esperados

- Selector calcula limite disponivel subtraindo compras ativas (incluindo parcelas futuras de faturas nao pagas).
- Compras canceladas ou ignoradas nao consomem limite do selector.
- Fatura aberta calcula corretamente o valor previsto.
- Fatura fechada calcula o valor fechado.
- Pagamentos parciais atualizam corretamente os indicadores de valor pago e restante da fatura.
- Pagamento de fatura gera transacao de pagamento na conta financeira de saida.

## Criterios de Aceite

- Compra no credito reduz limite disponivel conforme modelo real.
- Excesso de limite exibe alerta visual (soft warning) sem bloquear a transacao.
- Fatura fica acessivel via menu/rota direta global `/cards/statements/`.
- Usuario visualiza de forma intuitiva previsto, fechado, pago e pendente.

## Issues Sugeridas

- Criar selector de limite usado/disponivel em `cards/selectors.py`.
- Mostrar barra visual de limite na lista de cartoes.
- Criar rota/menu direto para faturas com visual moderno.
- Melhorar detalhe de fatura com resumos e confirmacao contextual de pagamento.

## SDD Baseline

Esta spec herda comandos, estrutura, estilo, estrategia de testes e boundaries de `docs/specs/000-sdd-baseline.md`.

## Assumptions

- Limite disponivel sera calculado a partir das transacoes ativas, nao persistido.
- Compra que excede o limite exibe alerta soft, permitindo o registro.
- Rota centralizada unificada `/cards/statements/` de faturas.

## Decisoes da Spec Review (Resolvidas)

- **Limite de Parcelamento:** Adotado o modelo real brasileiro, onde o valor total de compras ativas (mesmo futuras/parceladas) consome o limite do cartao imediatamente.
- **Bloqueio de Limite:** Adotado alerta visual soft para nao atrapalhar o fluxo de registros pós-fato.
- **Rota de Faturas:** Rota centralizada unificada `/cards/statements/` de todos os cartões.
- **Saldos de Beneficios:** Gestao avançada de cartões de benefícios movida para o backlog.
- **Edição em Faturas Fechadas:** Bloqueio de alteracao de compras vinculadas a faturas `PENDING` ou `PAID` fica para evolucao de backlog.

## Task Breakdown Inicial

- [ ] Task: Criar selector de limite usado/disponivel.
  - Acceptance: selector em `cards/selectors.py` calcula limites de credito considerando compras ativas e futuras.
  - Verify: testes de selector em `cards/tests/test_selectors.py`.
  - Files: `cards/selectors.py`, `cards/tests/test_selectors.py`.
- [ ] Task: Mostrar limite em lista de cartoes.
  - Acceptance: barra visual de progresso e limites em formato pt-BR na pagina `/cards/`.
  - Verify: teste de view e validacao visual manual.
  - Files: `cards/templates/cards/list.html`, `cards/views.py`.
- [ ] Task: Criar acesso direto a faturas no menu global.
  - Acceptance: menu lateral contem link direto para `/cards/statements/` com destaque ativo.
  - Verify: teste de navegacao e template.
  - Files: `templates/partials/nav_links.html`.
- [ ] Task: Melhorar detalhe de fatura com resumos e fluxo de pagamento.
  - Acceptance: tela de detalhes exibe indicadores de previsto, fechado, pago, restante e atalho contextual de confirmacao.
  - Verify: teste de view, template e validacao manual.
  - Files: `cards/templates/cards/statement_detail.html`, `cards/views.py`.
