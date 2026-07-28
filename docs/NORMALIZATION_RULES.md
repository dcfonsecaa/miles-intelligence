# Regras de normalização

O serviço `campaign_normalizer.py` recebe a saída bruta dos collectors. O Collector Livelo permanece responsável apenas por localizar e extrair blocos promocionais.

## Pontos

Formatos reconhecidos:

- `96.000 pontos`
- `96 mil pontos`
- `96k pontos`
- `74k pts`

Quando mais de um valor aparece no título, o maior valor é usado como total da campanha.

## Duração e pontos mensais

São reconhecidas expressões como:

- `em 12 meses`
- `por 12 meses`
- `durante 12 meses`

Quando existem pontos totais e duração, `monthly_points` é calculado pela divisão do total pela quantidade de meses.

## Tipo de campanha

O vocabulário controlado inclui:

- `subscription`
- `upgrade`
- `points_purchase`
- `transfer_bonus`
- `card_acquisition`
- `account_opening`
- `insurance`
- `investment`
- `shopping`
- `travel`
- `other`

Termos como “adesão”, “upgrade”, “compra de pontos” e “transferência bonificada” são reconhecidos mesmo com variações de caixa e acentuação.

## Modalidade

Valores:

- `monthly`
- `annual`
- `one_time`
- `recurring`
- `unknown`

O parser reconhece “mensal”, “anual”, “recorrente” e “adesão única”.

## Confiança

- `high`: quatro ou mais sinais estruturados foram identificados;
- `medium`: dois ou três sinais;
- `low`: menos de dois sinais.

## Limitações

- A normalização é determinística e baseada em regras; não utiliza IA externa.
- Textos ambíguos permanecem com valores `other`, `unknown` ou `null`.
- Custos só são considerados conhecidos quando fornecidos explicitamente.
- Mudanças na estrutura HTML das fontes podem exigir ajustes nos collectors.
