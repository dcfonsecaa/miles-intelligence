# Dashboard Web

## Objetivo

O dashboard transforma os dados existentes da API em uma visão operacional para acompanhar
campanhas de pontos e milhas. Ele não altera collectors, persistência, migrações, History Engine,
Intelligence Engine nem os contratos públicos do backend.

## Visões

- Cabeçalho com disponibilidade da API, última atualização e atualização global.
- KPIs de campanhas ativas, novas, alteradas, preliminares e que exigem atenção.
- Melhor campanha detectada no dia e melhor CPM entre campanhas com custo confirmado.
- Ranking único por HC Score, com filtros de fonte, tipo, modalidade, status, custo, análise,
  atenção e faixa de score.
- Notícias e linha do tempo formada pelos snapshots do History Engine.
- Estado operacional dos collectors Livelo, Esfera, Smiles, LATAM Pass e Azul Fidelidade.
- Modal com dados normalizados, explicação do score, recomendação, histórico, fonte oficial e
  payload bruto recolhível.

## Integração

O módulo `frontend/src/services/api.js` centraliza as requisições. O carregamento combina:

- `GET /health`;
- `GET /api/campaigns`;
- `GET /api/intelligence/highlights`;
- inteligência e histórico de cada campanha.

As consultas individuais usam os endpoints de cada collector. “Atualizar tudo” usa
`POST /api/campaigns/scan/all`. Uma falha parcial é apresentada ao usuário sem descartar os
resultados das demais fontes.

Configure outra origem por meio de `VITE_API_URL`. Sem configuração, o frontend usa
`http://localhost:8000/api`.

## Estados da interface

A interface trata carregamento, erro geral, ausência de dados, sucesso, atualização em andamento
e falha parcial. Os collectors mostram também estados ocioso, consultando, operacional e com falha.
O horário de coleta exibido no cartão é mantido somente na sessão atual; a API não possui ainda um
recurso persistente de observabilidade por collector.

## Segurança financeira

Somente campanhas com `cost_status = known`, `cost_brl` não nulo e CPM válido participam da
comparação de CPM. Campanhas sem confirmação exibem “Custo não confirmado”; nunca se converte
ausência de custo em `R$ 0,00`.

Uma recomendação atraente oriunda de análise preliminar é apresentada como “Aguardar confirmação”.
O modal reforça que a análise não representa avaliação financeira definitiva.

## Validação

```bash
cd frontend
npm install
npm run test
npm run build
```

A suíte cobre regras de formatação e seleção, carregamento, erro, vazio, ranking, filtros, atualização
global, falha parcial, proteção de custo e modal de detalhes.

## Limitações

- O dashboard não executa previsões nem chama LLM externo.
- A atualização depende da disponibilidade e do HTML das fontes oficiais.
- O status dos collectors não é persistido entre recarregamentos da página.
- A qualidade das recomendações segue os dados e limiares do Intelligence Engine atual.
