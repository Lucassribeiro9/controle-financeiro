# Fase 5 - Recorrencias e Previsoes

## Objetivo da fase

Implementar o fluxo inicial de recorrencias financeiras para gerar previsoes mensais sem marcar pagamento automaticamente, permitindo que o usuario confirme, ignore, ajuste ou reconcilie previsoes com transacoes reais.

Referencias:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## O que foi criado

### 1. App `recurrences`

Arquivos principais:

- `recurrences/apps.py`
- `recurrences/models.py`
- `recurrences/services.py`
- `recurrences/views.py`
- `recurrences/urls.py`
- `recurrences/admin.py`
- `recurrences/migrations/0001_initial.py`

Papel do app:

- Centralizar regras de recorrencias financeiras.
- Gerar previsoes a partir de recorrencias ativas.
- Expor operacoes iniciais para conferencia mensal das previsoes.

### 2. Model `Recurrence`

Arquivo principal:

- `recurrences/models.py`

Campos principais:

- `name`
- `expected_day`
- `frequency`
- `recurrence_type`
- `expected_amount`
- `is_active`
- `requires_confirmation`
- `account`
- `card`
- `created_at`
- `updated_at`

Frequencias iniciais:

- `monthly`
- `annual`
- `weekly`
- `biweekly`
- `quarterly`
- `custom`

Tipos iniciais:

- `income`
- `fixed_bill`
- `subscription`
- `other`

Regras iniciais:

- Dia esperado deve estar entre 1 e 31.
- Valor esperado deve ser positivo.
- Recorrencia de despesa fixa exige conta vinculada.
- Recorrencia de assinatura exige cartao vinculado.
- Recorrencias podem ser ativadas ou desativadas por `is_active`.
- Recorrencias exigem confirmacao por padrao.

### 3. Admin Django

Arquivo:

- `recurrences/admin.py`

O que foi feito:

- Registro do model `Recurrence` no Django Admin.
- Configuracao inicial de listagem, filtros, busca e ordenacao.

### 4. Rotas e views

Arquivos:

- `recurrences/urls.py`
- `recurrences/views.py`

Rotas implementadas:

- `recurrences/month/<int:year>/<int:month>/`
- `recurrences/forecasts/<int:transaction_id>/confirm/`
- `recurrences/forecasts/<int:transaction_id>/ignore/`
- `recurrences/forecasts/<int:transaction_id>/adjust/`

Comportamento:

- Listar previsoes de um mes.
- Confirmar uma previsao para virar transacao real pendente.
- Ignorar uma previsao somente naquele ciclo.
- Ajustar o valor previsto antes da confirmacao.

## Servicos implementados

Arquivo:

- `recurrences/services.py`

### `generate_monthly_recurrences_forecasts`

Responsabilidade:

- Gerar transacoes previstas para recorrencias ativas em um mes.
- Ajustar automaticamente o dia quando o mes tem menos dias que o esperado.
- Evitar duplicidade quando a mesma previsao ja existe.

Regras:

- A transacao gerada nasce com tipo `forecast`.
- A transacao gerada nasce com status `forecasted`.
- A geracao nao altera saldo de conta.

### `skip_recurrence_for_month`

Responsabilidade:

- Marcar como `ignored` uma previsao ja gerada para uma recorrencia em um mes especifico.

Regra importante:

- Ignorar uma previsao nao desativa a recorrencia inteira.

### `match_recurrence_with_transaction`

Responsabilidade:

- Associar uma transacao real a uma recorrencia.
- Validar conta e cartao esperados.
- Registrar o vinculo em `notes`.

### `has_relevant_amount_difference`

Responsabilidade:

- Detectar diferenca relevante entre valor esperado e valor real.

Uso previsto:

- Apoiar sugestoes futuras de revisao de recorrencia quando o valor real divergir do previsto.

## Fluxo atual de previsoes

1. Uma recorrencia ativa e cadastrada no Admin.
2. O servico mensal gera uma transacao `forecast`.
3. A previsao aparece na listagem mensal.
4. O usuario pode confirmar, ignorar ou ajustar a previsao.
5. Se uma transacao real for identificada, ela pode ser reconciliada com a recorrencia.

## Testes implementados na fase

### `Recurrence` (model)

Arquivo:

- `recurrences/tests/test_models.py`

Cobertura:

- Criacao de recorrencia de despesa fixa com conta.
- Validacao do dia esperado entre 1 e 31.
- Validacao de valor esperado positivo.
- Exigencia de conta para despesa fixa.
- Exigencia de cartao para assinatura.
- Validacao de `__str__`.

### Servicos de recorrencia

Arquivo:

- `recurrences/tests/test_services.py`

Cobertura:

- Geracao de previsao mensal.
- Garantia de que a previsao nasce como `forecasted`, nao paga.
- Ignorar previsao de uma recorrencia no mes.
- Reconciliar recorrencia com transacao real.
- Detectar diferenca relevante de valor.

### Views de previsao

Arquivo:

- `recurrences/tests/test_views.py`

Cobertura:

- Listagem de previsoes mensais.
- Confirmacao de previsao como transacao pendente.
- Ignorar previsao.
- Ajustar valor previsto.
- Rejeitar ajuste com valor invalido.

Execucao local:

```bash
python3 manage.py test recurrences
```

Ou pelo ambiente Docker:

```bash
docker compose run --rm web python manage.py test recurrences
```

## Status da fase

Fase 5 concluida (escopo MVP) em 2026-05-13.

O nucleo de recorrencias e previsoes foi criado e testado, incluindo model, admin, migrations, services, views e rotas iniciais para conferencia mensal.

## Backlog pos-fase

- Criar management command ou job agendado para disparar a geracao mensal.
- Evoluir reconciliacao para um vinculo estruturado em vez de anotacao textual.
- Criar fluxo dedicado para desativar ou cancelar recorrencias fora do Admin.
- Gerar sugestoes de revisao quando houver diferenca relevante de valor.
- Melhorar suporte pratico para frequencias diferentes de mensal.
