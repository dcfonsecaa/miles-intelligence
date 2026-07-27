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
2. Adicionar conectores Smiles, Esfera, LATAM Pass e Azul Fidelidade.
3. Criar histórico de versões de regulamentos.
4. Adicionar PostgreSQL e migrações.
5. Implementar autenticação.
6. Publicar frontend na Vercel e backend/banco na Railway.


## Primeiro collector oficial: Livelo

Com o backend em execução, dispare a coleta real pela documentação Swagger ou por:

```bash
curl -X POST http://localhost:8000/api/campaigns/scan/livelo
```

O collector acessa a página oficial de regulamentos ativos, identifica blocos promocionais, extrai título, link, período e quantidade explícita de pontos. Os valores financeiros permanecem zerados até que um parser específico de regulamento consiga confirmar o custo real; portanto, o score desta etapa é preliminar.
