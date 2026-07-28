# Collector Esfera v1

O collector consulta exclusivamente a página oficial de
[Termos e Condições da Esfera](https://www.esfera.com.vc/termos-e-condicoes).

Endpoint:

```text
POST /api/campaigns/scan/esfera
```

O parser identifica títulos promocionais em cabeçalhos e coleta, quando
presentes, texto de elegibilidade, parceiro informado no bloco, link real do
regulamento, pontos e vigência. A normalização compartilhada deriva tipo,
modalidade, datas, pontos mensais e confiança apenas quando houver evidência.

## Resposta

A resposta informa a fonte e as métricas `analyzed`, `inserted`, `updated`,
`unchanged`, `errors` e `campaigns`. Cada campanha inclui sua ação, mudança
histórica e os principais indicadores do Intelligence Engine.

## Limitações

- A extração é determinística e depende da estrutura HTML publicada pela Esfera.
- Conteúdo carregado exclusivamente por JavaScript pode não estar disponível
  para este collector HTTP.
- Percentuais de bônus permanecem no texto bruto enquanto não houver campo
  estruturado seguro no Campaign Model V2.
- Valores ausentes não são inferidos.
- Sem custo confirmado no regulamento, custo e CPM ficam nulos e a avaliação
  financeira permanece preliminar.
