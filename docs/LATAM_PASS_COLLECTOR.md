# Collector LATAM Pass v1

O collector monitora a página oficial de
[Ofertas LATAM Pass](https://latampass.latam.com/pt_br/ofertas). Ele aceita
somente links dos domínios oficiais LATAM Pass e LATAM Airlines que apontem para
páginas de promoção ou oferta.

Endpoint:

```text
POST /api/campaigns/scan/latam-pass
```

## Extração

Para cada oferta reconhecida, o collector registra quando disponível:

- título e URL oficial;
- parceiro;
- percentual de bônus;
- pontos ou milhas;
- vigência completa ou data final;
- elegibilidade e necessidade de cadastro;
- menção ao Clube LATAM Pass;
- limite e prazo de crédito;
- tipo de campanha;
- custo e status.

Percentual, cadastro obrigatório, menção ao Clube, limite e prazo de crédito
ficam em `extraction_notes` e no `raw_data` gerado pelo Campaign Normalizer
enquanto não houver campos estruturados próprios. Parceiro, pontos, datas e tipo
usam os campos existentes.

## Integrações

O collector utiliza a identidade compartilhada por `campaign_key` e passa pelos
mesmos History e Intelligence Engines das fontes anteriores. Uma coleta
inalterada não cria campanha nem snapshot redundante.

## Limitações

- A extração é determinística e depende do HTML entregue pela página oficial.
- Ofertas renderizadas exclusivamente por JavaScript podem não aparecer.
- Não são usados blogs ou agregadores como fonte.
- Dados ausentes não são inferidos.
- Sem custo confirmado, `cost_brl` e `cpm` permanecem nulos,
  `cost_status = unknown` e a análise financeira é preliminar.
