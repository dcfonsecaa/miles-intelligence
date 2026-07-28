# Miles Intelligence

MVP do Radar HC: uma plataforma de inteligência para detectar campanhas de pontos e milhas fora do padrão.

## O que já funciona

- API FastAPI
- Banco local SQLite para o primeiro teste
- Cadastro e listagem de campanhas
- Cálculo de CPM
- HC Score
- Anomaly Score
- Varredura simulada idempotente
- Collector Livelo v1 com leitura da página oficial de regulamentos ativos
- Arquitetura reutilizável de collectors e Collector Esfera v1
- Collector Smiles v1 com campanhas oficiais, transferências e Clube Smiles
- Collector LATAM Pass v1 com ofertas e promoções oficiais
- Collector Azul Fidelidade v1 e varredura agregada das cinco fontes
- Dashboard React + Vite + Bootstrap
- Testes automatizados do motor de pontuação

## Rodar sem Docker

### Backend

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API: `http://localhost:8000`
Documentação: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: `http://localhost:5173`

## Próximas etapas

1. Validar e fortalecer o Collector Livelo em diferentes formatos de regulamento.
2. Fortalecer os parsers conforme novos formatos oficiais forem publicados.
3. Criar histórico de versões de regulamentos.
4. Adicionar PostgreSQL e migrações.
5. Implementar autenticação.
6. Publicar frontend na Vercel e backend/banco na Railway.


## Primeiro collector oficial: Livelo

Com o backend em execução, dispare a coleta real pela documentação Swagger ou por:

```bash
curl -X POST http://localhost:8000/api/campaigns/scan/livelo
curl -X POST http://localhost:8000/api/campaigns/scan/esfera
curl -X POST http://localhost:8000/api/campaigns/scan/smiles
curl -X POST http://localhost:8000/api/campaigns/scan/latam-pass
curl -X POST http://localhost:8000/api/campaigns/scan/azul-fidelidade
curl -X POST http://localhost:8000/api/campaigns/scan/all
```

O collector acessa a página oficial de regulamentos ativos, identifica blocos promocionais, extrai título, link, período e quantidade explícita de pontos. Os valores financeiros permanecem desconhecidos (`null`) até que um parser específico de regulamento consiga confirmar o custo real; portanto, o score desta etapa é preliminar.

## Campaign Model V2

As campanhas passam por uma camada de normalização antes da persistência. O sistema registra separadamente programa, tipo, modalidade, parceiro, pontos totais e mensais, duração, período, elegibilidade, URLs de origem e regulamento, qualidade da extração e dados brutos.

### Situação do custo

- `known`: custo confirmado;
- `estimated`: custo estimado;
- `unknown`: custo não confirmado.

Campanhas com custo desconhecido usam `cost_brl = null` e `cpm = null`. Elas não são apresentadas como avaliação financeira definitiva.

### Tipos de campanha

Os tipos controlados incluem assinatura/adesão, upgrade, compra de pontos, transferência bonificada, aquisição de cartão, abertura de conta, seguro, investimento, shopping, viagem e outros.

### Identidade estável

`campaign_key` é derivada de empresa, título normalizado, URL do regulamento, tipo e modalidade. A chave permite deduplicar a mesma campanha sem confundir ofertas diferentes publicadas na mesma página.

Detalhes:

- [Campaign Model V2](docs/CAMPAIGN_MODEL_V2.md)
- [Regras de normalização](docs/NORMALIZATION_RULES.md)

### Limitações atuais

- O parser usa regras determinísticas e não utiliza IA externa.
- Campanhas ambíguas podem permanecer com classificação ou modalidade desconhecida.
- O Collector Livelo depende da estrutura HTML da página oficial.
- O Collector Esfera depende da estrutura HTML da página oficial de termos e condições.
- O Collector Smiles depende dos cartões e links publicados na página oficial de promoções.
- O Collector LATAM Pass depende dos cartões e links publicados na página oficial de ofertas.
- O Collector Azul Fidelidade depende dos cartões e links publicados na página oficial de ofertas em pontos.

## History Engine

Cada campanha possui snapshots imutáveis dos estados relevantes. Coletas idênticas não duplicam a campanha nem o histórico. Mudanças em pontos, custo, duração, datas, status ou título geram um novo snapshot, uma classificação e um resumo legível.

Tipos de mudança: `created`, `points_increased`, `points_decreased`, `cost_changed`, `duration_changed`, `dates_changed`, `status_changed`, `title_changed` e `multiple_changes`.

## Intelligence Engine v1

O motor compara a campanha atual com seu histórico e com campanhas da mesma empresa e tipo. Ele identifica recordes de pontos, variação percentual, posição histórica e recordes de CPM conhecido.

Recomendações possíveis: dados insuficientes, monitorar, analisar agora, potencialmente atrativa, atrativa e pouco atrativa. Uma campanha nunca é recomendada apenas por possuir muitos pontos.

Análises com custo desconhecido são **preliminares**: custo e CPM permanecem `null`, a confiança nunca é alta e o sistema solicita confirmação do regulamento. A análise só é **completa** quando o custo é conhecido.

Documentação:

- [History Engine](docs/HISTORY_ENGINE.md)
- [Intelligence Engine](docs/INTELLIGENCE_ENGINE.md)

O motor v1 usa regras determinísticas e limiares fixos. A qualidade da análise depende do volume de histórico comparável e não inclui previsão estatística nem APIs externas de IA.
