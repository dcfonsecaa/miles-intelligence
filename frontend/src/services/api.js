const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export async function listCampaigns() {
  const response = await fetch(`${API_URL}/campaigns`);
  if (!response.ok) throw new Error('Não foi possível carregar as campanhas.');
  return response.json();
}

export async function runDemoScan() {
  const response = await fetch(`${API_URL}/campaigns/scan-demo`, { method: 'POST' });
  if (!response.ok) throw new Error('Não foi possível executar a varredura.');
  return response.json();
}


export async function runLiveloScan() {
  const response = await fetch(`${API_URL}/campaigns/scan/livelo`, { method: 'POST' });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Não foi possível consultar a Livelo.');
  }
  return response.json();
}

export async function runEsferaScan() {
  const response = await fetch(`${API_URL}/campaigns/scan/esfera`, { method: 'POST' });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Não foi possível consultar a Esfera.');
  }
  return response.json();
}

export async function runSmilesScan() {
  const response = await fetch(`${API_URL}/campaigns/scan/smiles`, { method: 'POST' });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Não foi possível consultar a Smiles.');
  }
  return response.json();
}

export async function runLatamPassScan() {
  const response = await fetch(`${API_URL}/campaigns/scan/latam-pass`, { method: 'POST' });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Não foi possível consultar o LATAM Pass.');
  }
  return response.json();
}

export async function runAzulFidelidadeScan() {
  const response = await fetch(`${API_URL}/campaigns/scan/azul-fidelidade`, { method: 'POST' });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Não foi possível consultar o Azul Fidelidade.');
  }
  return response.json();
}

export async function runAllScans() {
  const response = await fetch(`${API_URL}/scan/all`, { method: 'POST' });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Não foi possível consultar todas as fontes.');
  }
  return response.json();
}

export async function getCampaignHistory(campaignId) {
  const response = await fetch(`${API_URL}/campaigns/${campaignId}/history`);
  if (!response.ok) throw new Error('Não foi possível carregar o histórico.');
  return response.json();
}

export async function getCampaignIntelligence(campaignId) {
  const response = await fetch(`${API_URL}/campaigns/${campaignId}/intelligence`);
  if (!response.ok) throw new Error('Não foi possível carregar a análise.');
  return response.json();
}

export async function getIntelligenceHighlights() {
  const response = await fetch(`${API_URL}/intelligence/highlights`);
  if (!response.ok) throw new Error('Não foi possível carregar os destaques.');
  return response.json();
}

export async function getIntelligenceDashboard() {
  const response = await fetch(`${API_URL}/intelligence/dashboard`);
  if (!response.ok) throw new Error('Não foi possível carregar o dashboard de inteligência.');
  return response.json();
}

export async function recalculateIntelligence() {
  const response = await fetch(`${API_URL}/campaigns/recalculate-intelligence`, { method: 'POST' });
  if (!response.ok) throw new Error('Não foi possível recalcular as análises.');
  return response.json();
}
