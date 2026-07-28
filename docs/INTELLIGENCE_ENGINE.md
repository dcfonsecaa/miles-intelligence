# Intelligence Engine v1

O Intelligence Engine é determinístico e não utiliza APIs externas de IA.

## Fontes de comparação

- campanha atual;
- snapshots da mesma campanha;
- campanhas da mesma empresa e tipo;
- campanha imediatamente anterior;
- média e máximo histórico de pontos;
- CPMs históricos conhecidos.

## Saída

- `analysis_status`
- `recommendation_level`
- `confidence_level`
- `historical_position`
- `points_change_percent`
- `is_points_record`
- `is_lowest_cpm_record`
- `attention_required`
- `reasons`
- `recommendation_text`
- `analyzed_at`

## Análise preliminar e completa

Quando `cost_status=unknown`, custo e CPM permanecem `null`, a análise é `preliminary` e a confiança nunca é alta. O texto sempre solicita confirmação de custo, elegibilidade e regulamento.

Uma análise só é `complete` quando o custo é conhecido e existe CPM calculado.

## Recomendações

- `insufficient_data`: não há histórico financeiro comparável;
- `monitor`: nenhuma mudança exige decisão imediata;
- `analyze_now`: mudança histórica relevante exige atenção;
- `potentially_attractive`: CPM conhecido abaixo da referência;
- `attractive`: combinação de recorde de pontos e menor CPM conhecido;
- `unattractive`: CPM conhecido significativamente acima da média.

Nenhuma recomendação depende apenas da quantidade de pontos.

## Atenção necessária

É ativada quando existe:

- recorde de pontos;
- aumento superior a 20%;
- CPM conhecido mais de 20% abaixo da média;
- mudança relevante de custo;
- encerramento em até sete dias.

## Limitações

- regras e limiares são fixos nesta versão;
- comparações dependem da quantidade e qualidade do histórico;
- classificações ambíguas do normalizador reduzem o conjunto comparável;
- não há previsão estatística nem análise semântica por IA.
