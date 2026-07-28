import { describe, expect, it } from 'vitest';
import {
  buildRecentHistory,
  filterCampaigns,
  formatCurrency,
  formatPoints,
  rankCampaigns,
  recommendationLabel,
  selectBestCampaignToday,
  selectBestKnownCpm,
} from './dashboardUtils';

const intelligence = {
  analysis_status: 'complete', recommendation_level: 'monitor', attention_required: false,
};
const base = {
  id: 1, company: 'Livelo', campaign_type: 'subscription', modality: 'annual',
  status: 'active', cost_status: 'unknown', cost_brl: null, cpm: null, hc_score: 40,
  detected_at: new Date().toISOString(), intelligence, history: [],
};

describe('regras do dashboard', () => {
  it('formata moeda e pontos em pt-BR', () => {
    expect(formatCurrency(1234.5)).toMatch(/1\.234,50/);
    expect(formatPoints(12345)).toBe('12.345');
  });

  it('não formata custo ausente como zero', () => {
    expect(formatCurrency(null)).toBe('—');
    expect(formatCurrency(undefined)).toBe('—');
  });

  it('seleciona a melhor campanha detectada hoje', () => {
    const winner = selectBestCampaignToday([{ ...base, id: 1 }, { ...base, id: 2, hc_score: 85 }]);
    expect(winner.id).toBe(2);
  });

  it('considera CPM somente quando o custo é conhecido', () => {
    const winner = selectBestKnownCpm([
      { ...base, id: 1, cpm: 0, cost_status: 'unknown' },
      { ...base, id: 2, cpm: 21, cost_status: 'known', cost_brl: 210 },
    ]);
    expect(winner.id).toBe(2);
  });

  it('ordena o ranking pelo HC Score', () => {
    expect(rankCampaigns([{ ...base, id: 1 }, { ...base, id: 2, hc_score: 80 }]).map((item) => item.id))
      .toEqual([2, 1]);
  });

  it('combina filtros de fonte, análise, atenção e faixa de score', () => {
    const result = filterCampaigns(
      [{ ...base }, { ...base, id: 2, company: 'Smiles', hc_score: 90 }],
      { source: 'Livelo', type: 'all', modality: 'all', status: 'all', cost: 'all', analysis: 'complete', attention: 'no', hcMin: 20, hcMax: 60 },
    );
    expect(result.map((item) => item.id)).toEqual([1]);
  });

  it('protege recomendações atraentes quando a análise é preliminar', () => {
    expect(recommendationLabel({
      ...base,
      intelligence: { ...intelligence, analysis_status: 'preliminary', recommendation_level: 'attractive' },
    })).toBe('Aguardar confirmação');
  });

  it('monta histórico recente com comparação ao snapshot anterior', () => {
    const history = buildRecentHistory([{
      ...base,
      title: 'Clube',
      history: [
        { id: 1, captured_at: '2026-01-01T10:00:00Z', bonus_points: 100 },
        { id: 2, captured_at: '2026-01-02T10:00:00Z', bonus_points: 200 },
      ],
    }]);
    expect(history[0].previous.bonus_points).toBe(100);
  });
});
