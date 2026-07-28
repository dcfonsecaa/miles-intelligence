const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const API_ROOT = API_URL.replace(/\/api\/?$/, '');

async function request(path, options = {}, fallbackMessage = 'Falha ao consultar a API.') {
  const response = await fetch(`${API_URL}${path}`, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || fallbackMessage);
  }
  return response.json();
}

export async function getApiStatus() {
  const response = await fetch(`${API_ROOT}/health`);
  if (!response.ok) throw new Error('API indisponível.');
  return response.json();
}

export const listCampaigns = () => request('/campaigns', {}, 'Não foi possível carregar as campanhas.');
export const getCampaign = (id) => request(`/campaigns/${id}`, {}, 'Não foi possível carregar a campanha.');
export const getCampaignRaw = (id) => request(`/campaigns/${id}/raw`, {}, 'Não foi possível carregar os dados brutos.');
export const getCampaignHistory = (id) => request(`/campaigns/${id}/history`, {}, 'Não foi possível carregar o histórico.');
export const getCampaignIntelligence = (id) => request(`/campaigns/${id}/intelligence`, {}, 'Não foi possível carregar a análise.');
export const getIntelligenceHighlights = () => request('/intelligence/highlights', {}, 'Não foi possível carregar os destaques.');
export const runDemoScan = () => request('/campaigns/scan-demo', { method: 'POST' }, 'Não foi possível executar a demonstração.');
export const runLiveloScan = () => request('/campaigns/scan/livelo', { method: 'POST' }, 'Não foi possível consultar a Livelo.');
export const runEsferaScan = () => request('/campaigns/scan/esfera', { method: 'POST' }, 'Não foi possível consultar a Esfera.');
export const runSmilesScan = () => request('/campaigns/scan/smiles', { method: 'POST' }, 'Não foi possível consultar a Smiles.');
export const runLatamPassScan = () => request('/campaigns/scan/latam-pass', { method: 'POST' }, 'Não foi possível consultar o LATAM Pass.');
export const runAzulFidelidadeScan = () => request('/campaigns/scan/azul-fidelidade', { method: 'POST' }, 'Não foi possível consultar o Azul Fidelidade.');
export const runAllScans = () => request('/campaigns/scan/all', { method: 'POST' }, 'Não foi possível consultar todas as fontes.');
export const recalculateIntelligence = () => request('/campaigns/recalculate-intelligence', { method: 'POST' }, 'Não foi possível recalcular as análises.');

export async function loadDashboardData() {
  const [campaigns, highlights] = await Promise.all([
    listCampaigns(),
    getIntelligenceHighlights(),
  ]);
  const enriched = await Promise.all(campaigns.map(async (campaign) => {
    const [intelligenceResult, historyResult] = await Promise.allSettled([
      getCampaignIntelligence(campaign.id),
      getCampaignHistory(campaign.id),
    ]);
    return {
      ...campaign,
      intelligence: intelligenceResult.status === 'fulfilled'
        ? intelligenceResult.value
        : null,
      history: historyResult.status === 'fulfilled' ? historyResult.value : [],
      partialError: intelligenceResult.status === 'rejected'
        || historyResult.status === 'rejected',
    };
  }));
  return { campaigns: enriched, highlights };
}
