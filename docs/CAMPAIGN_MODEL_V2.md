# Campaign Model V2

O Campaign Model V2 transforma campanhas coletadas em registros normalizados, preparados para o futuro History Engine e Intelligence Engine.

## Campos principais

- Identidade: `id`, `campaign_key`, `company`, `program_name`.
- Classificação: `campaign_type`, `modality`, `partner_name`, `category`, `status`.
- Conteúdo: `title`, `normalized_title`, `summary`, `eligibility`, `extraction_notes`.
- Origem: `source_url`, `regulation_url`, `raw_data`.
- Benefício: `bonus_points`, `duration_months`, `monthly_points`.
- Período: `start_date`, `end_date`, `detected_at`, `updated_at`.
- Financeiro: `cost_brl`, `cost_status`, `cpm`, `hc_score`, `anomaly_score`.
- Qualidade: `extraction_confidence`.

## Custo

`cost_status` aceita:

- `known`: custo explicitamente confirmado;
- `estimated`: custo estimado, ainda sujeito a validação;
- `unknown`: custo ausente ou não confirmado.

Custo desconhecido nunca é representado como zero. Nesse caso, `cost_brl` e `cpm` são `null`, e o HC Score permanece preliminar.

## Identidade e deduplicação

`campaign_key` é o SHA-256 determinístico da combinação normalizada:

1. empresa;
2. título normalizado;
3. URL real do regulamento;
4. tipo da campanha;
5. modalidade.

Assim, campanhas diferentes publicadas na mesma página de origem permanecem registros distintos.

## Migração SQLite

Na inicialização, a rotina `migrate_campaign_model_v2`:

1. detecta o schema legado;
2. lê todos os registros antes de alterar a tabela;
3. cria a tabela V2 sem unicidade em `source_url`;
4. normaliza e reinsere os registros preservando seus IDs;
5. converte campanhas Livelo legadas com custo zero para `cost_brl = null`, `cost_status = unknown` e `cpm = null`;
6. remove a tabela legada somente após a cópia terminar dentro da transação.

A rotina é idempotente e não apaga o arquivo SQLite.

## Compatibilidade de API

Os endpoints existentes continuam disponíveis:

- `GET /api/campaigns`
- `POST /api/campaigns`
- `POST /api/campaigns/scan-demo`
- `POST /api/campaigns/scan/livelo`

Foram adicionados:

- `GET /api/campaigns/{campaign_id}`
- `GET /api/campaigns/{campaign_id}/raw`
