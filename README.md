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

1. Substituir a varredura simulada por conectores de fontes oficiais.
2. Criar histórico de versões de regulamentos.
3. Adicionar PostgreSQL e migrações.
4. Implementar autenticação.
5. Publicar frontend na Vercel e backend/banco na Railway.
