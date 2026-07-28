import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import * as api from './services/api';

vi.mock('./services/api', () => ({
  getApiStatus: vi.fn(), getCampaign: vi.fn(), getCampaignHistory: vi.fn(),
  getCampaignIntelligence: vi.fn(), getCampaignRaw: vi.fn(), loadDashboardData: vi.fn(),
  runAllScans: vi.fn(), runAzulFidelidadeScan: vi.fn(), runEsferaScan: vi.fn(),
  runLatamPassScan: vi.fn(), runLiveloScan: vi.fn(), runSmilesScan: vi.fn(),
}));

const analysis = {
  campaign_id: 1, analysis_status: 'preliminary', recommendation_level: 'attractive',
  confidence_level: 'low', historical_position: 'Primeira observação',
  points_change_percent: null, is_points_record: false, is_lowest_cpm_record: false,
  attention_required: true, reasons: ['Custo ainda não confirmado'],
  recommendation_text: 'Aguarde o regulamento oficial.', analyzed_at: '2026-07-28T12:00:00Z',
};
const campaign = {
  id: 1, company: 'Livelo', program_name: 'Livelo', campaign_type: 'subscription',
  modality: 'annual', title: 'Clube Livelo 20 mil pontos', source_url: 'https://example.com',
  regulation_url: 'https://example.com/regulamento', category: 'clube', bonus_points: 20000,
  duration_months: 12, monthly_points: 1667, start_date: '2026-07-28', end_date: '2026-08-10',
  cost_brl: null, cost_status: 'unknown', eligibility: 'Novos assinantes', status: 'active',
  extraction_confidence: 'high', summary: 'Campanha de adesão.', campaign_key: 'livelo-1',
  cpm: null, hc_score: 74.5, anomaly_score: 0, detected_at: new Date().toISOString(),
  updated_at: '2026-07-28T12:00:00Z', intelligence: analysis,
  history: [{ id: 1, campaign_id: 1, captured_at: '2026-07-28T12:00:00Z', bonus_points: 20000, change_type: 'created', change_summary: 'Campanha criada' }],
};
const highlights = {
  new_campaigns: [{ campaign, intelligence: analysis, latest_change_type: 'created' }],
  changed_campaigns: [], points_records: [], attention_required: [{ campaign, intelligence: analysis }],
  unknown_cost: [{ campaign, intelligence: analysis }], preliminary_analyses: [{ campaign, intelligence: analysis }],
};

beforeEach(() => {
  vi.clearAllMocks();
  api.getApiStatus.mockResolvedValue({ status: 'ok' });
  api.loadDashboardData.mockResolvedValue({ campaigns: [campaign], highlights });
  api.getCampaign.mockResolvedValue(campaign);
  api.getCampaignHistory.mockResolvedValue(campaign.history);
  api.getCampaignIntelligence.mockResolvedValue(analysis);
  api.getCampaignRaw.mockResolvedValue({ raw: { source: 'fixture' } });
});

describe('dashboard profissional', () => {
  it('exibe o estado de carregamento', () => {
    api.loadDashboardData.mockReturnValue(new Promise(() => {}));
    render(<App />);
    expect(screen.getByLabelText('Carregando dashboard')).toBeInTheDocument();
  });

  it('renderiza dashboard carregado e status da API', async () => {
    render(<App />);
    expect(await screen.findByText('Ranking de campanhas')).toBeInTheDocument();
    expect(screen.getByText('API online')).toBeInTheDocument();
    expect(screen.getAllByText('Fontes monitoradas')).toHaveLength(2);
  });

  it('exibe erro da API de dados e permite tentar novamente', async () => {
    api.loadDashboardData.mockRejectedValueOnce(new Error('API fora do ar'));
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('API fora do ar');
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument();
  });

  it('mostra melhor campanha do dia e custo não confirmado sem falso zero', async () => {
    render(<App />);
    await screen.findByText('Ranking de campanhas');
    expect(screen.getAllByText(campaign.title).length).toBeGreaterThan(0);
    expect(screen.getByText('Custo não confirmado')).toBeInTheDocument();
    expect(screen.queryByText('R$ 0,00')).not.toBeInTheDocument();
  });

  it('exibe estado vazio quando não há CPM confirmado', async () => {
    render(<App />);
    expect(await screen.findByText('Nenhuma campanha com custo confirmado para calcular o CPM.')).toBeInTheDocument();
  });

  it('filtra o ranking por fonte', async () => {
    render(<App />);
    await screen.findByText('Ranking de campanhas');
    fireEvent.change(screen.getByLabelText('Fonte'), { target: { value: 'Smiles' } });
    expect(screen.getByText('Nenhuma campanha corresponde aos filtros selecionados.')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Limpar filtros'));
    expect(within(screen.getByTestId('campaign-ranking')).getByText(campaign.title)).toBeInTheDocument();
  });

  it('executa atualização global e sinaliza falha parcial por fonte', async () => {
    api.runAllScans.mockResolvedValue({
      inserted: 1, updated: 0,
      sources: [{ source: 'Livelo', status: 'success', errors: 0 }, { source: 'Smiles', status: 'error', errors: 1 }],
    });
    render(<App />);
    await screen.findByText('Ranking de campanhas');
    fireEvent.click(screen.getByRole('button', { name: 'Atualizar tudo' }));
    expect(await screen.findByText(/Atualização parcial: 1 fonte/)).toBeInTheDocument();
    expect(api.runAllScans).toHaveBeenCalledOnce();
  });

  it('abre detalhes, histórico e dados brutos da campanha', async () => {
    render(<App />);
    await screen.findByText('Ranking de campanhas');
    fireEvent.click(screen.getByRole('button', { name: 'Detalhes' }));
    expect(await screen.findByRole('dialog')).toHaveTextContent('Análise preliminar');
    expect(screen.getByText('Por que recebeu este score')).toBeInTheDocument();
    expect(screen.getByText('Dados brutos da coleta')).toBeInTheDocument();
    await waitFor(() => expect(api.getCampaignRaw).toHaveBeenCalledWith(1));
  });
});
