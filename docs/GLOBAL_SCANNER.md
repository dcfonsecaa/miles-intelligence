# Scanner Global

O endpoint `POST /api/scan/all` executa sequencialmente Livelo, Esfera, Smiles,
LATAM Pass e Azul Fidelidade usando o agregador compatível já disponível em
`POST /api/campaigns/scan/all`.

A resposta contém:

- métricas consolidadas;
- resultado individual de cada fonte;
- campanhas coletadas;
- `ranking` único por `campaign_key`, ordenado por HC Score decrescente.

Quando a mesma campanha aparece mais de uma vez no resultado, o ranking conserva
a versão de maior HC Score. Empates são ordenados por empresa e título para
produzir resposta determinística. Uma falha em uma fonte não interrompe as
seguintes.
