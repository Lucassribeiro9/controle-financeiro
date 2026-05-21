# Fase 10 - Taxas CDI e Rendimentos

## Objetivo da fase

Implementar o primeiro corte da Fase 10 com foco exclusivo em CDI manual e estimativas educativas de rendimento por porcentagem do CDI.

Ficaram fora desta etapa:

- dólar;
- Banco Central;
- CDI automático;
- TR;
- poupança;
- imposto;
- IOF;
- liquidez;
- comparação entre produtos financeiros.

Referências:

- `docs/plans/scope.md`
- `docs/plans/controle-financeiro-implementation-plan.md`

## O que foi criado

### 1. App `rates`

Arquivos principais:

- `rates/models.py`
- `rates/admin.py`
- `rates/forms.py`
- `rates/services.py`
- `rates/selectors.py`
- `rates/views.py`
- `rates/urls.py`
- `rates/templates/rates/list.html`
- `rates/templates/rates/rate_form.html`
- `rates/templates/rates/yield_config_form.html`
- `rates/templates/rates/simulation.html`

O app foi registrado em `INSTALLED_APPS`, incluído em `project/urls.py` e ganhou link `Rendimentos` no menu lateral.

## Models

### `ReferenceRate`

Responsabilidade:

- guardar histórico local de taxas de referência;
- nesta fase, aceitar somente CDI anual cadastrado manualmente.

Campos principais:

- `rate_type`;
- `date`;
- `value`;
- `periodicity`;
- `source`;
- `notes`;
- timestamps.

Representação:

```text
10,65% ao ano = 0.1065
```

Ou seja, a taxa é salva como decimal financeiro, não como `10.65`.

Regras:

- `value` deve ser maior que zero;
- somente `rate_type = cdi`;
- somente `periodicity = annual`;
- não pode existir taxa duplicada para mesmo tipo, data e periodicidade.

### `AccountYieldConfig`

Responsabilidade:

- configurar como uma conta deve ter rendimento estimado.

Campos principais:

- `account`;
- `yield_type`;
- `cdi_percentage`;
- `is_active`;
- timestamps.

Representação do percentual:

```text
100% CDI = 100.0000
110% CDI = 110.0000
80% CDI = 80.0000
```

Regras:

- rendimento `% do CDI` exige `cdi_percentage` maior que zero;
- rendimento `Sem rendimento` não deve ter percentual;
- configuração inativa não entra no resumo de estimativas.

## Fórmula CDI

Entrada:

```text
amount = valor inicial
months = quantidade de meses
annual_cdi_rate = CDI anual em decimal, exemplo 0.1065
cdi_percentage = percentual do CDI, exemplo 100.0000
```

Cálculo:

```python
cdi_multiplier = cdi_percentage / Decimal("100")
effective_annual_rate = annual_cdi_rate * cdi_multiplier
monthly_rate = ((Decimal("1") + effective_annual_rate) ** (Decimal("1") / Decimal("12"))) - Decimal("1")
final_amount = amount * ((Decimal("1") + monthly_rate) ** months)
estimated_yield = final_amount - amount
```

Valores monetários finais são arredondados para `Decimal("0.01")`.

## Services

Services criados:

- `save_reference_rate`
- `get_latest_reference_rate`
- `get_latest_cdi_rate`
- `simulate_cdi_yield`
- `estimate_account_yield`

Regras importantes:

- `save_reference_rate` chama `full_clean()` antes de salvar;
- `get_latest_cdi_rate` retorna erro claro quando não há CDI cadastrado;
- `simulate_cdi_yield` valida valores positivos;
- `estimate_account_yield` usa o saldo atual da conta quando `amount` não é informado;
- conta sem configuração ativa retorna erro de validação;
- rendimento `Sem rendimento` retorna rendimento zero.

## Selectors

Selectors criados:

- `get_latest_rates`
- `get_rate_history`
- `get_active_yield_configs`
- `get_account_yield_summary`

O resumo de rendimento não quebra a tela inteira quando falta CDI. Nesse caso, o item da conta volta com:

```python
{
    "config": config,
    "estimate": None,
    "error": "mensagem controlada",
}
```

## Views e Templates

Views criadas:

- `rates_page`
- `reference_rate_create_page`
- `yield_config_create_page`
- `yield_config_update_page`
- `yield_simulation_page`

Rotas:

- `/rates/`
- `/rates/create/`
- `/rates/yields/create/`
- `/rates/yields/<id>/edit/`
- `/rates/simulate/`

Tela principal de rendimentos exibe:

- último CDI anual cadastrado;
- data da taxa;
- histórico recente;
- contas configuradas;
- saldo projetado em 12 meses;
- rendimento estimado;
- acesso à simulação.

## Exemplos

Com:

```text
amount = 1000.00
annual_cdi_rate = 0.1200
months = 12
```

Exemplos de resultado:

| Percentual | Taxa anual efetiva | Valor final aproximado | Rendimento aproximado |
| --- | ---: | ---: | ---: |
| 80% CDI | 0.0960 | R$ 1.096,00 | R$ 96,00 |
| 100% CDI | 0.1200 | R$ 1.120,00 | R$ 120,00 |
| 110% CDI | 0.1320 | R$ 1.132,00 | R$ 132,00 |

## Testes

Coberturas criadas:

- `rates/tests/test_models.py`
- `rates/tests/test_services.py`
- `rates/tests/test_selectors.py`
- `rates/tests/test_views.py`

Cenários cobertos:

- cadastro válido de CDI anual;
- rejeição de taxa zero ou negativa;
- unicidade de CDI por tipo, data e periodicidade;
- configuração 100% CDI;
- rejeição de configuração CDI sem percentual;
- rejeição de percentual zero ou negativo;
- rendimento `none`;
- busca do último CDI;
- simulações de CDI;
- estimativas por saldo da conta e por valor informado;
- erro controlado quando falta CDI;
- renderização das telas;
- criação e edição via POST;
- link de rendimentos no sidebar.

## Backlog futuro

- Buscar CDI automaticamente em fonte confiável.
- Integrar Banco Central.
- Cadastrar dólar e outras taxas de câmbio.
- Converter contas em USD para estimativa em BRL.
- Considerar TR e poupança.
- Considerar imposto, IOF e prazo.
- Comparar rendimento estimado entre contas/produtos.
- Melhorar UX com gráficos e evolução mês a mês.
