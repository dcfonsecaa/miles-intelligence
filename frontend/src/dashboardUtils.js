export const SOURCE_CONFIG = [
  { key: 'livelo', name: 'Livelo', initials: 'LI' },
  { key: 'esfera', name: 'Esfera', initials: 'ES' },
  { key: 'smiles', name: 'Smiles', initials: 'SM' },
  { key: 'latam-pass', name: 'LATAM Pass', initials: 'LP' },
  { key: 'azul-fidelidade', name: 'Azul Fidelidade', initials: 'AZ' },
];
export const TYPE_LABELS = {
  subscription: 'Adesão', upgrade: 'Upgrade', points_purchase: 'Compra de pontos',
  transfer_bonus: 'Transferência', card_acquisition: 'Aquisição de cartão',
  account_opening: 'Abertura de conta', insurance: 'Seguro', investment: 'Investimento',
  shopping: 'Shopping', travel: 'Viagem', other: 'Outro',
};
export const RECOMMENDATION_LABELS = {
  insufficient_data: 'Dados insuficientes', monitor: 'Monitorar', analyze_now: 'Analisar agora',
  potentially_attractive: 'Potencialmente atrativa', attractive: 'Atrativa', unattractive: 'Pouco atrativa',
};
export const CONFIDENCE_LABELS = { high: 'Alta', medium: 'Média', low: 'Baixa' };
export const CHANGE_LABELS = {
  created: 'Nova campanha', unchanged: 'Sem mudança', points_increased: 'Aumento de pontos',
  points_decreased: 'Redução de pontos', cost_changed: 'Mudança de custo',
  duration_changed: 'Mudança de prazo', dates_changed: 'Mudança de vigência',
  status_changed: 'Mudança de status', title_changed: 'Mudança de título',
  multiple_changes: 'Múltiplas mudanças',
};
export const formatCurrency = (value) => value === null || value === undefined
  ? '—' : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
export const formatPoints = (value) => new Intl.NumberFormat('pt-BR').format(value || 0);
export const formatPercent = (value) => value === null || value === undefined
  ? '—' : `${new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value)}%`;
export const formatScore = (value) => Number(value || 0).toFixed(1).replace('.', ',');
export const formatDate = (value) => value
  ? new Intl.DateTimeFormat('pt-BR', { timeZone: 'UTC' }).format(new Date(value)) : '—';
export const formatDateTime = (value) => value
  ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
  : 'Ainda não disponível';

export function recommendationLabel(campaign) {
  const intelligence = campaign.intelligence;
  if (!intelligence) return 'Análise indisponível';
  if (intelligence.analysis_status === 'preliminary'
    && ['attractive', 'potentially_attractive'].includes(intelligence.recommendation_level)) {
    return 'Aguardar confirmação';
  }
  return RECOMMENDATION_LABELS[intelligence.recommendation_level] || intelligence.recommendation_level;
}
export function selectBestCampaignToday(campaigns, now = new Date()) {
  const day = now.toLocaleDateString('pt-BR');
  return campaigns
    .filter((campaign) => new Date(campaign.detected_at).toLocaleDateString('pt-BR') === day)
    .sort((a, b) => Number(b.hc_score) - Number(a.hc_score))[0] || null;
}
export function selectBestKnownCpm(campaigns) {
  return campaigns
    .filter((campaign) => campaign.cost_status === 'known' && campaign.cost_brl !== null
      && Number.isFinite(campaign.cpm) && campaign.cpm >= 0)
    .sort((a, b) => a.cpm - b.cpm)[0] || null;
}
export function rankCampaigns(campaigns) {
  return [...campaigns].sort((a, b) => Number(b.hc_score) - Number(a.hc_score)
    || a.company.localeCompare(b.company, 'pt-BR'));
}
export function filterCampaigns(campaigns, filters) {
  return campaigns.filter((campaign) => {
    const intelligence = campaign.intelligence;
    const hcScore = Number(campaign.hc_score || 0);
    return (filters.source === 'all' || campaign.company === filters.source)
      && (filters.type === 'all' || campaign.campaign_type === filters.type)
      && (filters.modality === 'all' || campaign.modality === filters.modality)
      && (filters.status === 'all' || campaign.status === filters.status)
      && (filters.cost === 'all' || (filters.cost === 'known'
        ? campaign.cost_status === 'known' : campaign.cost_status !== 'known'))
      && (filters.analysis === 'all' || intelligence?.analysis_status === filters.analysis)
      && (filters.attention === 'all' || (filters.attention === 'yes'
        ? intelligence?.attention_required === true : intelligence?.attention_required !== true))
      && hcScore >= Number(filters.hcMin || 0) && hcScore <= Number(filters.hcMax || 100);
  });
}
export function buildRecentHistory(campaigns) {
  return campaigns.flatMap((campaign) => {
    const sorted = [...(campaign.history || [])]
      .sort((a, b) => new Date(a.captured_at) - new Date(b.captured_at));
    return sorted.map((snapshot, index) => ({
      ...snapshot, campaign, previous: index > 0 ? sorted[index - 1] : null,
    }));
  }).sort((a, b) => new Date(b.captured_at) - new Date(a.captured_at));
}
