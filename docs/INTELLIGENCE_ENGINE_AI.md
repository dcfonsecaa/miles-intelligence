# Intelligence Engine AI-ready

`GET /api/intelligence/{campaign_id}/ai-analysis` gera uma análise explicável
sob demanda, sem persistir novo estado e sem alterar o cálculo do HC Score.

A resposta inclui:

- resumo automático da campanha;
- explicação dos componentes usados no HC Score;
- até cinco campanhas semelhantes do mesmo tipo;
- recomendação e justificativa em linguagem clara;
- estado do provedor de previsão.

## Recomendações

As regras podem produzir “Vale aproveitar”, “Aguarde”, “Promoção acima da
média” ou “Monitore”. Campanhas sem custo confirmado nunca recebem recomendação
financeira definitiva, mesmo quando o volume de pontos está acima da média.

## Arquitetura futura

`PredictionProvider` define o contrato para um futuro modelo estatístico ou
provedor de IA. A implementação padrão, `NoPredictionProvider`, informa
explicitamente que previsões não estão configuradas. Nenhum LLM externo, token,
segredo ou chamada de rede foi introduzido nesta versão.

O motor atual `CampaignInsightEngine` é determinístico, testável e substituível,
permitindo adicionar previsões posteriormente sem quebrar a resposta da API ou
os motores History/Intelligence existentes.
