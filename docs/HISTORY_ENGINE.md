# History Engine

O History Engine registra estados relevantes de cada campanha em `campaign_snapshots`.

## Snapshot

Cada snapshot contém título, pontos, duração, pontos mensais, custo, situação do custo, período, status, regulamento, dados brutos e um `content_hash`.

Campos operacionais como `updated_at` e `detected_at` não participam do hash. Uma coleta idêntica retorna `action=unchanged` e não cria snapshot redundante.

## Tipos de mudança

- `created`
- `unchanged` — retornado pela coleta, mas não persistido como snapshot redundante
- `points_increased`
- `points_decreased`
- `cost_changed`
- `duration_changed`
- `dates_changed`
- `status_changed`
- `title_changed`
- `multiple_changes`

## Identidade

A busca usa primeiro `campaign_key`. Quando uma alteração de conteúdo modifica a própria chave, o motor tenta um fallback por empresa, URL do regulamento, tipo e modalidade. O fallback só é aceito quando encontra exatamente uma campanha, evitando unir campanhas ambíguas.

## Migração

Depois da criação das novas tabelas, `migrate_history_engine` cria um snapshot inicial para toda campanha existente que ainda não possua histórico. A rotina preserva IDs, não altera campanhas e pode ser executada repetidamente.

No futuro PostgreSQL, a criação de schema deverá migrar para uma ferramenta versionada; a rotina automática atual é voltada ao SQLite do MVP.
