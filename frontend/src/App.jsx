import { useEffect, useMemo, useState } from 'react';
import {
  getApiStatus, getCampaign, getCampaignHistory, getCampaignIntelligence, getCampaignRaw,
  loadDashboardData, runAllScans, runAzulFidelidadeScan, runEsferaScan, runLatamPassScan,
  runLiveloScan, runSmilesScan,
} from './services/api';
import {
  CHANGE_LABELS, CONFIDENCE_LABELS, SOURCE_CONFIG, TYPE_LABELS, buildRecentHistory,
  filterCampaigns, formatCurrency, formatDate, formatDateTime, formatPercent, formatPoints,
  formatScore, rankCampaigns, recommendationLabel, selectBestCampaignToday, selectBestKnownCpm,
} from './dashboardUtils';

const EMPTY_HIGHLIGHTS = { new_campaigns: [], changed_campaigns: [], points_records: [], attention_required: [], unknown_cost: [], preliminary_analyses: [] };
const INITIAL_FILTERS = { source: 'all', type: 'all', modality: 'all', status: 'all', cost: 'all', analysis: 'all', attention: 'all', hcMin: 0, hcMax: 100 };
const SCANNERS = { livelo: runLiveloScan, esfera: runEsferaScan, smiles: runSmilesScan, 'latam-pass': runLatamPassScan, 'azul-fidelidade': runAzulFidelidadeScan };

export default function App() {
  const [campaigns, setCampaigns] = useState([]);
  const [highlights, setHighlights] = useState(EMPTY_HIGHLIGHTS);
  const [apiOnline, setApiOnline] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [updating, setUpdating] = useState(false);
  const [details, setDetails] = useState(null);
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [sourceState, setSourceState] = useState(() => Object.fromEntries(
    SOURCE_CONFIG.map(({ key }) => [key, { status: 'idle', lastScan: null, errors: 0 }]),
  ));

  async function load({ quiet = false } = {}) {
    if (!quiet) setLoading(true);
    setError('');
    const [healthResult, dataResult] = await Promise.allSettled([getApiStatus(), loadDashboardData()]);
    setApiOnline(healthResult.status === 'fulfilled');
    if (dataResult.status === 'rejected') {
      setError(dataResult.reason?.message || 'Não foi possível carregar o dashboard.');
    } else {
      setCampaigns(dataResult.value.campaigns);
      setHighlights(dataResult.value.highlights);
      const partial = dataResult.value.campaigns.filter((item) => item.partialError).length;
      if (partial) setNotice(`${partial} campanha(s) estão com dados complementares indisponíveis.`);
    }
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function updateAll() {
    setUpdating(true);
    setNotice('Atualizando todas as fontes oficiais...');
    const capturedAt = new Date().toISOString();
    try {
      const result = await runAllScans();
      const failed = result.sources?.filter((source) => source.status === 'error') || [];
      setSourceState((current) => {
        const next = { ...current };
        (result.sources || []).forEach((source) => {
          const config = SOURCE_CONFIG.find((item) => item.name === source.source);
          if (config) next[config.key] = {
            status: source.status === 'error' ? 'error' : 'success', lastScan: capturedAt,
            errors: source.errors || (source.status === 'error' ? 1 : 0),
          };
        });
        return next;
      });
      setNotice(failed.length
        ? `Atualização parcial: ${failed.length} fonte(s) apresentaram falha. As demais foram preservadas.`
        : `Atualização concluída: ${result.inserted} nova(s) e ${result.updated} alterada(s).`);
      await load({ quiet: true });
    } catch (scanError) {
      setNotice('');
      setError(scanError.message);
    } finally {
      setUpdating(false);
    }
  }

  async function scanSource(source) {
    setSourceState((current) => ({ ...current, [source.key]: { ...current[source.key], status: 'running' } }));
    try {
      const result = await SCANNERS[source.key]();
      setSourceState((current) => ({ ...current, [source.key]: { status: 'success', lastScan: new Date().toISOString(), errors: result.errors || 0 } }));
      setNotice(`${source.name}: ${result.inserted} nova(s), ${result.updated} alterada(s).`);
      await load({ quiet: true });
    } catch (scanError) {
      setSourceState((current) => ({ ...current, [source.key]: { ...current[source.key], status: 'error', lastScan: new Date().toISOString(), errors: current[source.key].errors + 1 } }));
      setNotice(`${source.name}: ${scanError.message}`);
    }
  }

  async function openDetails(campaign) {
    setDetails({ loading: true, campaign });
    try {
      const [fullCampaign, history, intelligence, raw] = await Promise.all([
        getCampaign(campaign.id), getCampaignHistory(campaign.id),
        getCampaignIntelligence(campaign.id), getCampaignRaw(campaign.id),
      ]);
      setDetails({ loading: false, campaign: fullCampaign, history, intelligence, raw: raw.raw });
    } catch (detailError) {
      setDetails({ loading: false, campaign, error: detailError.message });
    }
  }

  const filtered = useMemo(() => rankCampaigns(filterCampaigns(campaigns, filters)), [campaigns, filters]);
  const bestToday = selectBestCampaignToday(campaigns);
  const bestCpm = selectBestKnownCpm(campaigns);
  const recentHistory = buildRecentHistory(campaigns).slice(0, 8);
  const lastUpdated = campaigns.map((item) => item.updated_at).filter(Boolean).sort().at(-1);
  const activeCount = campaigns.filter((item) => ['active', 'detected'].includes(item.status)).length;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="container-fluid dashboard-container">
          <div className="brand-block">
            <span className="brand-mark">MI</span>
            <div><h1>Miles Intelligence</h1><p>Inteligência de campanhas de pontos e milhas</p></div>
          </div>
          <div className="header-actions">
            <div className="system-meta">
              <span className={`status-pill ${apiOnline ? 'online' : 'offline'}`}><i /> API {apiOnline ? 'online' : 'indisponível'}</span>
              <span>Última atualização: {formatDateTime(lastUpdated)}</span>
            </div>
            <button className="btn btn-light update-button" onClick={updateAll} disabled={updating}>
              <span className={updating ? 'spinner-border spinner-border-sm' : ''} />{updating ? ' Atualizando...' : 'Atualizar tudo'}
            </button>
          </div>
        </div>
      </header>

      <div className="container-fluid dashboard-container dashboard-body">
        {notice && <div className="alert alert-info dashboard-alert" role="status">{notice}</div>}
        {error && <div className="state-panel error-state" role="alert">
          <strong>Não foi possível carregar os dados.</strong><span>{error}</span>
          <button className="btn btn-outline-danger btn-sm" onClick={() => load()}>Tentar novamente</button>
        </div>}

        {loading ? <DashboardSkeleton /> : !error && <>
          <section className="kpi-grid" aria-label="Indicadores principais">
            <Kpi label="Campanhas ativas" value={activeCount} tone="blue" />
            <Kpi label="Novas campanhas" value={highlights.new_campaigns.length} tone="green" />
            <Kpi label="Alterações detectadas" value={highlights.changed_campaigns.length} tone="amber" />
            <Kpi label="Exigem atenção" value={highlights.attention_required.length} tone="red" />
            <Kpi label="Análises preliminares" value={highlights.preliminary_analyses.length} tone="violet" />
            <Kpi label="Fontes monitoradas" value={SOURCE_CONFIG.length} tone="slate" />
          </section>

          <section className="spotlight-grid">
            <Spotlight eyebrow="Melhor campanha do dia" campaign={bestToday} empty="Nenhuma campanha detectada hoje." onDetails={openDetails} />
            <Spotlight eyebrow="Melhor CPM confirmado" campaign={bestCpm} empty="Nenhuma campanha com custo confirmado para calcular o CPM." cpm onDetails={openDetails} />
          </section>

          <section className="content-grid">
            <div className="panel ranking-panel">
              <PanelHeading title="Ranking de campanhas" subtitle={`${filtered.length} resultado(s)`} />
              <Filters filters={filters} setFilters={setFilters} />
              <CampaignRanking campaigns={filtered} onDetails={openDetails} />
            </div>
            <aside className="side-stack">
              <div className="panel"><PanelHeading title="Novidades" subtitle="Movimentos recentes" /><NewsList highlights={highlights} /></div>
              <div className="panel"><PanelHeading title="Histórico recente" subtitle="Linha do tempo" /><HistoryTimeline items={recentHistory} /></div>
            </aside>
          </section>

          <section className="panel sources-panel">
            <PanelHeading title="Fontes monitoradas" subtitle="Coletores oficiais" />
            <div className="source-grid">{SOURCE_CONFIG.map((source) => (
              <SourceCard key={source.key} source={source} state={sourceState[source.key]}
                count={campaigns.filter((item) => item.company === source.name).length} onScan={() => scanSource(source)} />
            ))}</div>
          </section>
        </>}
      </div>
      {details && <CampaignModal details={details} onClose={() => setDetails(null)} />}
    </main>
  );
}

function Kpi({ label, value, tone }) {
  return <article className={`kpi-card ${tone}`}><span>{label}</span><strong>{value}</strong></article>;
}
function PanelHeading({ title, subtitle }) {
  return <div className="panel-heading"><div><h2>{title}</h2><p>{subtitle}</p></div></div>;
}
function Spotlight({ eyebrow, campaign, empty, cpm = false, onDetails }) {
  return <article className="spotlight-card">
    <span className="eyebrow">{eyebrow}</span>
    {!campaign ? <p className="empty-copy">{empty}</p> : <>
      <div className="spotlight-head"><div><h2>{campaign.title}</h2><span>{campaign.company}</span></div><Score value={campaign.hc_score} /></div>
      <div className="spotlight-metrics">
        <span><small>Pontos</small>{formatPoints(campaign.bonus_points)}</span>
        <span><small>{cpm ? 'CPM' : 'Recomendação'}</small>{cpm ? formatCurrency(campaign.cpm) : recommendationLabel(campaign)}</span>
      </div>
      <button className="link-button" onClick={() => onDetails(campaign)}>Ver análise completa →</button>
    </>}
  </article>;
}

function Filters({ filters, setFilters }) {
  const update = (key) => (event) => setFilters((current) => ({ ...current, [key]: event.target.value }));
  return <div className="filter-area">
    <div className="filter-grid">
      <FilterSelect label="Fonte" value={filters.source} onChange={update('source')}><option value="all">Todas</option>{SOURCE_CONFIG.map((source) => <option key={source.key}>{source.name}</option>)}</FilterSelect>
      <FilterSelect label="Tipo" value={filters.type} onChange={update('type')}><option value="all">Todos</option>{Object.entries(TYPE_LABELS).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</FilterSelect>
      <FilterSelect label="Modalidade" value={filters.modality} onChange={update('modality')}><option value="all">Todas</option><option value="monthly">Mensal</option><option value="annual">Anual</option><option value="one_time">Única</option><option value="recurring">Recorrente</option><option value="unknown">Não informada</option></FilterSelect>
      <FilterSelect label="Status" value={filters.status} onChange={update('status')}><option value="all">Todos</option><option value="active">Ativa</option><option value="detected">Detectada</option><option value="expired">Expirada</option><option value="unavailable">Indisponível</option></FilterSelect>
      <FilterSelect label="Custo" value={filters.cost} onChange={update('cost')}><option value="all">Todos</option><option value="known">Confirmado</option><option value="unknown">Não confirmado</option></FilterSelect>
      <FilterSelect label="Análise" value={filters.analysis} onChange={update('analysis')}><option value="all">Todas</option><option value="complete">Completa</option><option value="preliminary">Preliminar</option></FilterSelect>
      <FilterSelect label="Atenção" value={filters.attention} onChange={update('attention')}><option value="all">Todas</option><option value="yes">Sim</option><option value="no">Não</option></FilterSelect>
      <label className="filter-field score-filter"><span>HC Score: {filters.hcMin}–{filters.hcMax}</span><div>
        <input aria-label="HC Score mínimo" type="number" min="0" max="100" value={filters.hcMin} onChange={update('hcMin')} />
        <input aria-label="HC Score máximo" type="number" min="0" max="100" value={filters.hcMax} onChange={update('hcMax')} />
      </div></label>
    </div>
    <button className="clear-filters" onClick={() => setFilters(INITIAL_FILTERS)}>Limpar filtros</button>
  </div>;
}
function FilterSelect({ label, children, ...props }) {
  return <label className="filter-field"><span>{label}</span><select {...props}>{children}</select></label>;
}

function CampaignRanking({ campaigns, onDetails }) {
  if (!campaigns.length) return <EmptyState text="Nenhuma campanha corresponde aos filtros selecionados." />;
  return <div className="ranking-list" data-testid="campaign-ranking">{campaigns.map((campaign, index) => (
    <article className="ranking-row" key={campaign.id}>
      <span className="rank-number">{index + 1}</span>
      <div className="campaign-main"><div className="campaign-title-line">
        <strong>{campaign.title}</strong>
        {campaign.intelligence?.attention_required && <span className="tag attention">Atenção</span>}
        {campaign.intelligence?.analysis_status === 'preliminary' && <span className="tag preliminary">Preliminar</span>}
      </div><span>{campaign.company} · {TYPE_LABELS[campaign.campaign_type] || campaign.campaign_type}</span></div>
      <div className="ranking-metric"><small>Pontos</small><strong>{formatPoints(campaign.bonus_points)}</strong></div>
      <div className="ranking-metric cost"><small>Custo / CPM</small>{campaign.cost_status === 'known'
        ? <strong>{formatCurrency(campaign.cost_brl)} · {formatCurrency(campaign.cpm)}</strong>
        : <strong>Custo não confirmado</strong>}</div>
      <Score value={campaign.hc_score} />
      <button className="btn btn-outline-primary btn-sm" onClick={() => onDetails(campaign)}>Detalhes</button>
    </article>
  ))}</div>;
}
function Score({ value }) {
  return <span className="score-badge" aria-label={`HC Score ${formatScore(value)}`}><strong>{formatScore(value)}</strong><small>HC</small></span>;
}
function NewsList({ highlights }) {
  const news = [
    ...highlights.new_campaigns.map((item) => ({ ...item, kind: 'Nova' })),
    ...highlights.changed_campaigns.map((item) => ({ ...item, kind: 'Alterada' })),
  ].slice(0, 5);
  if (!news.length) return <EmptyState text="Nenhuma novidade registrada." compact />;
  return <div className="news-list">{news.map((item) => <div className="news-item" key={`${item.kind}-${item.campaign.id}`}>
    <span className={`news-dot ${item.kind === 'Nova' ? 'new' : 'changed'}`} /><div><strong>{item.campaign.title}</strong><span>{item.kind} · {item.campaign.company}</span></div>
  </div>)}</div>;
}
function HistoryTimeline({ items }) {
  if (!items.length) return <EmptyState text="O histórico aparecerá após as coletas." compact />;
  return <div className="timeline">{items.map((item) => <div className="timeline-item" key={item.id}><i /><div>
    <strong>{CHANGE_LABELS[item.change_type] || item.change_type}</strong><span>{item.campaign.title}</span><small>{formatDateTime(item.captured_at)}</small>
    {item.previous && item.previous.bonus_points !== item.bonus_points && <small>{formatPoints(item.previous.bonus_points)} → {formatPoints(item.bonus_points)} pontos</small>}
  </div></div>)}</div>;
}
function SourceCard({ source, state, count, onScan }) {
  const statusLabel = { idle: 'Aguardando consulta', running: 'Consultando...', success: 'Operacional', error: 'Com falha' }[state.status];
  return <article className="source-card">
    <div className="source-card-head"><span className={`source-logo source-${source.key}`}>{source.initials}</span><strong>{source.name}</strong></div>
    <dl><div><dt>Campanhas</dt><dd>{count}</dd></div><div><dt>Última coleta</dt><dd>{formatDateTime(state.lastScan)}</dd></div></dl>
    <div className="source-footer"><span className={`source-status ${state.status}`}><i />{statusLabel}{state.errors ? ` · ${state.errors} erro(s)` : ''}</span>
      <button className="btn btn-sm btn-outline-primary" onClick={onScan} disabled={state.status === 'running'}>Consultar</button></div>
  </article>;
}

function CampaignModal({ details, onClose }) {
  const { campaign } = details;
  return <><div className="modal d-block" tabIndex="-1" role="dialog" aria-modal="true">
    <div className="modal-dialog modal-xl modal-dialog-scrollable"><div className="modal-content detail-modal">
      <div className="modal-header"><div><span className="eyebrow">{campaign.company}</span><h2 className="modal-title">{campaign.title}</h2></div>
        <button type="button" className="btn-close" onClick={onClose} aria-label="Fechar" /></div>
      <div className="modal-body">{details.loading && <DashboardSkeleton compact />}
        {details.error && <div className="alert alert-danger">{details.error}</div>}
        {!details.loading && !details.error && <CampaignDetailContent details={details} />}</div>
    </div></div>
  </div><div className="modal-backdrop show" /></>;
}
function CampaignDetailContent({ details }) {
  const { campaign, history, intelligence, raw } = details;
  return <div className="detail-layout"><section>
    <div className="detail-score"><Score value={campaign.hc_score} /><div><strong>{recommendationLabel({ ...campaign, intelligence })}</strong><span>{intelligence.recommendation_text}</span></div></div>
    {intelligence.analysis_status === 'preliminary' && <div className="preliminary-warning">Análise preliminar: o custo não confirmado não representa avaliação financeira definitiva.</div>}
    <h3>Resumo inteligente</h3><p>{campaign.summary || intelligence.recommendation_text}</p>
    <h3>Por que recebeu este score</h3><ul className="reason-list">{intelligence.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
    <h3>Histórico e mudanças</h3><HistoryTimeline items={(history || []).map((item, index) => ({ ...item, campaign, previous: index ? history[index - 1] : null })).reverse()} />
  </section><aside>
    <h3>Dados normalizados</h3><dl className="detail-data">
      <Detail label="Programa" value={campaign.program_name || campaign.company} />
      <Detail label="Tipo" value={TYPE_LABELS[campaign.campaign_type] || campaign.campaign_type} />
      <Detail label="Modalidade" value={campaign.modality || 'Não informada'} />
      <Detail label="Pontos" value={formatPoints(campaign.bonus_points)} />
      <Detail label="Custo" value={campaign.cost_status === 'known' ? formatCurrency(campaign.cost_brl) : 'Não confirmado'} />
      <Detail label="CPM" value={campaign.cost_status === 'known' ? formatCurrency(campaign.cpm) : 'Não calculado'} />
      <Detail label="Vigência" value={`${formatDate(campaign.start_date)} a ${formatDate(campaign.end_date)}`} />
      <Detail label="Elegibilidade" value={campaign.eligibility || 'Não informada'} />
      <Detail label="Confiança da extração" value={CONFIDENCE_LABELS[campaign.extraction_confidence] || campaign.extraction_confidence} />
      <Detail label="Posição histórica" value={intelligence.historical_position} />
      <Detail label="Variação de pontos" value={formatPercent(intelligence.points_change_percent)} />
    </dl>
    {(campaign.regulation_url || campaign.source_url) && <a className="btn btn-primary w-100" href={campaign.regulation_url || campaign.source_url} target="_blank" rel="noreferrer">Abrir fonte oficial</a>}
    <details className="raw-data"><summary>Dados brutos da coleta</summary><pre>{JSON.stringify(raw, null, 2)}</pre></details>
  </aside></div>;
}
function Detail({ label, value }) { return <div><dt>{label}</dt><dd>{value}</dd></div>; }
function EmptyState({ text, compact = false }) { return <div className={`empty-state ${compact ? 'compact' : ''}`}><span>—</span><p>{text}</p></div>; }
function DashboardSkeleton({ compact = false }) {
  return <div className={`dashboard-skeleton ${compact ? 'compact' : ''}`} aria-label="Carregando dashboard">{[1, 2, 3, 4, 5, 6].map((item) => <div key={item} />)}</div>;
}
