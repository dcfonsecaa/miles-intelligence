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
