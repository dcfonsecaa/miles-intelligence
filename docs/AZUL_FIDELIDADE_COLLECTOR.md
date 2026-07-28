# Collector Azul Fidelidade v1

O collector monitora a página oficial de
[Ofertas em Pontos do Azul Fidelidade](https://www.voeazul.com.br/br/pt/ofertas/pontos).
Ele aceita apenas links no domínio oficial `voeazul.com.br` relacionados a
ofertas ou ao programa de fidelidade.

Endpoint individual:

```text
POST /api/campaigns/scan/azul-fidelidade
```

Endpoint agregado:

```text
POST /api/campaigns/scan/all
```

## Extração

O collector registra quando disponível:

- título e URL oficial;
- parceiro e percentual de bônus;
- pontos, modalidade e vigência;
- elegibilidade e necessidade de cadastro;
- menção ao Clube Azul;
- limite e prazo de crédito;
- tipo de campanha;
- custo e status.

Percentual, cadastro, menção ao Clube, limite e prazo ficam em
`extraction_notes` e `raw_data` enquanto o Campaign Model V2 não possuir campos
específicos. Parceiro, pontos, datas, modalidade e tipo usam os campos atuais.

## Integrações

Todas as campanhas usam `campaign_key`, History Engine e Intelligence Engine.
Coletas iguais não criam duplicatas ou snapshots redundantes. O dashboard
permite consultar a fonte individualmente ou executar as cinco fontes em
sequência.

## Limitações

- A extração é determinística e depende do HTML oficial.
- Conteúdo renderizado exclusivamente por JavaScript pode não ser coletado.
- Blogs e agregadores não são usados como fonte.
- Dados ausentes não são inferidos.
- Sem custo confirmado, `cost_brl` e `cpm` ficam nulos,
  `cost_status = unknown` e a análise financeira permanece preliminar.
