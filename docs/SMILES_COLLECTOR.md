# Collector Smiles v1

O collector monitora links publicados na página oficial de
[Promoções da Smiles](https://www.smiles.com.br/pt/promocao). São aceitos apenas
links do domínio `smiles.com.br` para páginas de campanhas e promoções.

Endpoint:

```text
POST /api/campaigns/scan/smiles
```

## Extração

Para cada cartão promocional, o collector registra quando disponível:

- título e URL oficial da campanha;
- programa e empresa Smiles;
- parceiro reconhecido no texto;
- tipo de campanha;
- vigência;
- elegibilidade e necessidade de cadastro;
- menção ao Clube Smiles;
- maior percentual explícito de bônus;
- limite por CPF e prazo de crédito;
- custo e status.

Percentual, cadastro obrigatório, menção ao Clube, limite e prazo de crédito
ficam em `extraction_notes` e no `raw_data` produzido pelo normalizador, pois o
Campaign Model V2 ainda não possui campos estruturados específicos para esses
conceitos. Pontos, datas, parceiro e tipo usam os campos existentes.

## Identidade e histórico

A identidade compartilhada considera empresa, programa, título normalizado,
parceiro, tipo, modalidade e URL real. Cada execução passa pelos mesmos History
e Intelligence Engines usados pelas fontes Livelo e Esfera.

## Limitações

- O parser é determinístico e depende do HTML entregue pela página de promoções.
- Campanhas renderizadas apenas após execução de JavaScript podem não aparecer.
- O collector não acessa páginas de blogs ou agregadores.
- Dados ausentes não são inferidos.
- Sem confirmação financeira no regulamento, `cost_brl` e `cpm` permanecem
  nulos, `cost_status` é `unknown` e a análise é preliminar.
