# Arquitetura de collectors

Os collectors oficiais ficam em `backend/app/collectors` e compartilham o fluxo
definido por `BaseCollector`:

1. `fetch`: consulta a fonte oficial com timeout, User-Agent identificável,
   validação HTTP, limite de 5 MB e validação básica de HTML;
2. `parse`: converte o HTML em objetos `CampaignCreate` sem inventar campos;
3. `normalize`: aplica o Campaign Normalizer e gera a `campaign_key`;
4. `identify`: procura a campanha persistida por identidade estável;
5. `persist`: integra deduplicação, History Engine e Intelligence Engine;
6. `run`: coordena o fluxo e retorna métricas padronizadas por fonte.

Regras específicas permanecem nas subclasses. O registro em `registry.py`
resolve o collector pelo identificador usado na API. O collector Livelo é um
adaptador do parser anterior, preservando a rota
`POST /api/campaigns/scan/livelo`.

## Identidade

A chave considera empresa, programa, título normalizado, parceiro, tipo,
modalidade e URL real do regulamento. Campanhas diferentes hospedadas na mesma
página não são deduplicadas apenas pela URL.

## Persistência

Toda fonte utiliza a mesma função de persistência. Uma campanha nova cria
snapshot e análise; uma campanha inalterada não cria snapshot redundante; uma
mudança gera o tipo correspondente no histórico e recalcula a inteligência.

Custos não confirmados são persistidos como `cost_brl = null`,
`cost_status = unknown` e `cpm = null`. A análise resultante é preliminar.

## Como adicionar uma fonte

Crie uma subclasse de `BaseCollector`, implemente `source_name`, `source_url` e
`parse`, registre-a em `registry.py`, exponha a rota e cubra o parser com fixture
local. Os testes não devem depender de consultas reais.
