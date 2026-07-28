import { useEffect, useState } from 'react';
import {
  getCampaignHistory,
  getCampaignIntelligence,
  getIntelligenceDashboard,
  getIntelligenceHighlights,
  listCampaigns,
  recalculateIntelligence,
  runAllScans,
  runAzulFidelidadeScan,
  runEsferaScan,
  runDemoScan,
  runLiveloScan,
  runLatamPassScan,
  runSmilesScan,
} from './services/api';

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const number = new Intl.NumberFormat('pt-BR');
const typeLabels = {
  subscription: 'Adesão', upgrade: 'Upgrade', points_purchase: 'Compra de pontos',
  transfer_bonus: 'Transferência', card_acquisition: 'Aquisição de cartão',
  account_opening: 'Abertura de conta', insurance: 'Seguro', investment: 'Investimento',
  shopping: 'Shopping', travel: 'Viagem', other: 'Outro',
};
const recommendationLabels = {
  insufficient_data: 'Dados insuficientes', monitor: 'Monitorar', analyze_now: 'Analisar agora',
  potentially_attractive: 'Potencialmente atrativa', attractive: 'Atrativa', unattractive: 'Pouco atrativa',
};
const confidenceLabels = { high: 'Alta', medium: 'Média', low: 'Baixa' };
const changeLabels = {
  created: 'Campanha criada', unchanged: 'Sem mudança', points_increased: 'Pontos aumentaram',
  points_decreased: 'Pontos diminuíram', cost_changed: 'Custo alterado',
  duration_changed: 'Duração alterada', dates_changed: 'Datas alteradas',
  status_changed: 'Status alterado', title_changed: 'Título alterado',
  multiple_changes: 'Múltiplas mudanças',
};

const emptyHighlights = {
  new_campaigns: [], changed_campaigns: [], points_records: [],
  attention_required: [], unknown_cost: [], preliminary_analyses: [],
};
const emptyDashboard = {
  best_campaign_today: null, ranking: [], recent_history: [],
  last_updated_at: null, programs: [],
};

export default function App() {
  const [campaigns, setCampaigns] = useState([]);
  const [highlights, setHighlights] = useState(emptyHighlights);
  const [dashboard, setDashboard] = useState(emptyDashboard);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [details, setDetails] = useState(null);
  const [sourceFilter, setSourceFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [programFilter, setProgramFilter] = useState('all');

  async function load() {
    setLoading(true);
    try {
      const [items, summary, dashboardData] = await Promise.all([
        listCampaigns(),
        getIntelligenceHighlights(),
        getIntelligenceDashboard(),
      ]);
      const enriched = await Promise.all(items.map(async (campaign) => ({
        ...campaign,
        intelligence: await getCampaignIntelligence(campaign.id),
      })));
      setCampaigns(enriched);
      setHighlights(summary);
      setDashboard(dashboardData);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function runScan(kind) {
    const sourceLabels = {
      livelo: 'Livelo',
      esfera: 'Esfera',
      smiles: 'Smiles',
      'latam-pass': 'LATAM Pass',
      'azul-fidelidade': 'Azul Fidelidade',
      all: 'Todas as fontes',
    };
    setMessage(sourceLabels[kind]
      ? `Consultando a fonte oficial da ${sourceLabels[kind]}...`
      : 'Executando demonstração...');
    try {
      const scans = {
        livelo: runLiveloScan,
        esfera: runEsferaScan,
        smiles: runSmilesScan,
        'latam-pass': runLatamPassScan,
        'azul-fidelidade': runAzulFidelidadeScan,
        all: runAllScans,
        demo: runDemoScan,
      };
      const result = await scans[kind]();
      const source = result.source ? ` (${result.source})` : kind === 'all' ? ' (todas as fontes)' : '';
      const failedSources = result.sources?.filter((item) => item.status === 'error').length || 0;
      setMessage(
        `Coleta concluída${source}: ${result.inserted} nova(s), ${result.updated} alterada(s), `
        + `${result.unchanged} sem mudança e ${result.errors} erro(s)`
        + `${failedSources ? ` em ${failedSources} fonte(s)` : ''}.`,
      );
      await load();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function recalculate() {
    setMessage('Recalculando análises determinísticas...');
    try {
      const result = await recalculateIntelligence();
      setMessage(`${result.recalculated} análise(s) recalculada(s).`);
      await load();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function openDetails(campaign) {
    try {
      const [history, intelligence] = await Promise.all([
        getCampaignHistory(campaign.id),
        getCampaignIntelligence(campaign.id),
      ]);
      setDetails({ campaign, history, intelligence });
    } catch (error) {
      setMessage(error.message);
    }
  }

  useEffect(() => { load(); }, []);

  const filteredCampaigns = campaigns.filter((item) => (
    (sourceFilter === 'all' || item.company === sourceFilter)
    && (typeFilter === 'all' || item.campaign_type === typeFilter)
    && (programFilter === 'all' || (item.program_name || item.company) === programFilter)
  ));
  const dashboardRanking = dashboard.ranking.filter(
    (item) => programFilter === 'all'
      || (item.campaign.program_name || item.campaign.company) === programFilter,
  );
  const recentHistory = dashboard.recent_history.filter(
    (item) => programFilter === 'all'
      || (item.program_name || item.company) === programFilter,
  );
  const bestToday = dashboard.best_campaign_today
    && (programFilter === 'all'
      || (dashboard.best_campaign_today.campaign.program_name
        || dashboard.best_campaign_today.campaign.company) === programFilter)
    ? dashboard.best_campaign_today
    : null;

  return (
    <main className="min-vh-100 bg-light">
      <header className="hero text-white py-5">
        <div className="container py-3">
          <span className="badge text-bg-warning mb-3">History + Intelligence Engine v1</span>
          <h1 className="display-5 fw-bold">Miles Intelligence</h1>
          <p className="lead col-lg-9">Histórico de campanhas, mudanças detectadas e análises determinísticas.</p>
          <div className="d-flex flex-wrap gap-2">
            <button className="btn btn-light btn-lg" onClick={() => runScan('livelo')}>Consultar Livelo</button>
            <button className="btn btn-warning btn-lg" onClick={() => runScan('esfera')}>Consultar Esfera</button>
            <button className="btn btn-success btn-lg" onClick={() => runScan('smiles')}>Consultar Smiles</button>
            <button className="btn btn-danger btn-lg" onClick={() => runScan('latam-pass')}>Consultar LATAM Pass</button>
            <button className="btn btn-info btn-lg" onClick={() => runScan('azul-fidelidade')}>Consultar Azul Fidelidade</button>
            <button className="btn btn-dark btn-lg" onClick={() => runScan('all')}>Consultar Tudo</button>
            <button className="btn btn-outline-light btn-lg" onClick={() => runScan('demo')}>Rodar demonstração</button>
            <button className="btn btn-outline-warning btn-lg" onClick={recalculate}>Recalcular análises</button>
          </div>
        </div>
      </header>

      <section className="container-fluid px-4 py-5">
        {message && <div className="alert alert-info">{message}</div>}
        <IntelligenceDashboard
          bestToday={bestToday}
          ranking={dashboardRanking}
          recentHistory={recentHistory}
          lastUpdatedAt={dashboard.last_updated_at}
          onOpen={openDetails}
        />
        <div className="row g-3 mb-4">
          {['Livelo', 'Esfera', 'Smiles', 'LATAM Pass', 'Azul Fidelidade'].map((source) => (
            <div className="col-md-6" key={source}>
              <div className="card border-0 shadow-sm h-100">
                <div className="card-body d-flex justify-content-between align-items-center">
                  <div>
                    <div className="text-secondary small">Fonte oficial</div>
                    <div className="h5 mb-0">{source}</div>
                  </div>
                  <span className="badge text-bg-dark">
                    {campaigns.filter((item) => item.company === source).length} campanha(s)
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="row g-3 mb-4">
          <Stat title="Total geral de campanhas" value={campaigns.length} />
          <Stat title="Campanhas novas" value={highlights.new_campaigns.length} />
          <Stat title="Campanhas alteradas" value={highlights.changed_campaigns.length} />
          <Stat title="Recordes de pontos" value={highlights.points_records.length} />
          <Stat title="Análises preliminares" value={highlights.preliminary_analyses.length} />
          <Stat title="Exigem atenção" value={highlights.attention_required.length} />
        </div>

        <div className="card border-0 shadow-sm">
          <div className="card-body p-4">
            <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
              <h2 className="h4 mb-0">Campanhas analisadas</h2>
              <div className="d-flex flex-wrap gap-2">
                <select
                  className="form-select form-select-sm"
                  aria-label="Filtrar por programa"
                  value={programFilter}
                  onChange={(event) => setProgramFilter(event.target.value)}
                >
                  <option value="all">Todos os programas</option>
                  {dashboard.programs.map((program) => (
                    <option value={program} key={program}>{program}</option>
                  ))}
                </select>
                <select
                  className="form-select form-select-sm"
                  aria-label="Filtrar por fonte"
                  value={sourceFilter}
                  onChange={(event) => setSourceFilter(event.target.value)}
                >
                  <option value="all">Todas as fontes</option>
                  <option value="Livelo">Livelo</option>
                  <option value="Esfera">Esfera</option>
                  <option value="Smiles">Smiles</option>
                  <option value="LATAM Pass">LATAM Pass</option>
                  <option value="Azul Fidelidade">Azul Fidelidade</option>
                </select>
                <select
                  className="form-select form-select-sm"
                  aria-label="Filtrar por tipo"
                  value={typeFilter}
                  onChange={(event) => setTypeFilter(event.target.value)}
                >
                  <option value="all">Todos os tipos</option>
                  {Object.entries(typeLabels).map(([value, label]) => (
                    <option value={value} key={value}>{label}</option>
                  ))}
                </select>
                <button className="btn btn-outline-dark btn-sm" onClick={load}>Atualizar</button>
              </div>
            </div>
            {loading ? <p>Carregando...</p> : campaigns.length === 0 ? (
              <p className="text-secondary mb-0">Nenhuma campanha salva.</p>
            ) : filteredCampaigns.length === 0 ? (
              <p className="text-secondary mb-0">Nenhuma campanha corresponde aos filtros.</p>
            ) : (
              <div className="table-responsive">
                <table className="table align-middle">
                  <thead><tr>
                    <th>Empresa</th><th>Campanha</th><th>Tipo</th><th>Pontos</th>
                    <th>Custo / CPM</th><th>Análise</th><th>Recomendação</th><th>Confiança</th><th></th>
                  </tr></thead>
                  <tbody>{filteredCampaigns.map((item) => (
                    <tr key={item.id}>
                      <td className="fw-semibold">{item.company}</td>
                      <td>
                        <div>{item.title}</div>
                        {item.intelligence.is_points_record && <span className="badge text-bg-success me-1">Recorde de pontos</span>}
                        {item.intelligence.attention_required && <span className="badge text-bg-warning">Atenção</span>}
                      </td>
                      <td>{typeLabels[item.campaign_type] || item.campaign_type}</td>
                      <td>
                        <div>{number.format(item.bonus_points)}</div>
                        <small>{item.monthly_points === null ? 'Mensal não calculado' : `${number.format(item.monthly_points)}/mês`}</small>
                      </td>
                      <td>
                        <div>{item.cost_status === 'unknown' ? 'Custo desconhecido' : money.format(item.cost_brl)}</div>
                        <small>{item.cpm === null ? 'CPM não calculado' : `CPM ${money.format(item.cpm)}`}</small>
                      </td>
                      <td>
                        {item.intelligence.analysis_status === 'preliminary'
                          ? <span className="badge text-bg-secondary">Análise preliminar</span>
                          : <span className="badge text-bg-primary">Análise completa</span>}
                      </td>
                      <td>{recommendationLabels[item.intelligence.recommendation_level]}</td>
                      <td>{confidenceLabels[item.intelligence.confidence_level]}</td>
                      <td><button className="btn btn-sm btn-outline-primary" onClick={() => openDetails(item)}>Detalhes</button></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </section>

      {details && <CampaignDetails details={details} onClose={() => setDetails(null)} />}
    </main>
  );
}

function IntelligenceDashboard({
  bestToday, ranking, recentHistory, lastUpdatedAt, onOpen,
}) {
  return (
    <section className="mb-4" aria-label="Dashboard Intelligence">
      <div className="d-flex flex-wrap justify-content-between align-items-end gap-2 mb-3">
        <div>
          <div className="text-uppercase text-secondary small fw-semibold">Dashboard Intelligence</div>
          <h2 className="h3 mb-0">Visão geral das oportunidades</h2>
        </div>
        <small className="text-secondary">
          Última atualização: {lastUpdatedAt
            ? new Date(lastUpdatedAt).toLocaleString('pt-BR')
            : 'Ainda não disponível'}
        </small>
      </div>
      <div className="row g-3">
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm h-100">
            <div className="card-body">
              <div className="text-secondary small">Melhor campanha do dia</div>
              {bestToday ? (
                <>
                  <h3 className="h5 mt-2">{bestToday.campaign.title}</h3>
                  <div className="display-5 fw-bold">{bestToday.campaign.hc_score.toFixed(1)}</div>
                  <div className="text-secondary mb-3">HC Score · {bestToday.campaign.company}</div>
                  <button className="btn btn-outline-primary btn-sm" onClick={() => onOpen(bestToday.campaign)}>
                    Ver análise
                  </button>
                </>
              ) : <p className="text-secondary mt-2 mb-0">Nenhuma campanha detectada hoje.</p>}
            </div>
          </div>
        </div>
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm h-100">
            <div className="card-body">
              <h3 className="h6">Ranking das campanhas</h3>
              <div className="vstack gap-2">
                {ranking.slice(0, 5).map((item, index) => (
                  <button
                    className="btn btn-light text-start d-flex justify-content-between"
                    key={item.campaign.id}
                    onClick={() => onOpen(item.campaign)}
                  >
                    <span>{index + 1}. {item.campaign.title}</span>
                    <strong>{item.campaign.hc_score.toFixed(1)}</strong>
                  </button>
                ))}
                {ranking.length === 0 && <span className="text-secondary">Sem campanhas no ranking.</span>}
              </div>
            </div>
          </div>
        </div>
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm h-100">
            <div className="card-body">
              <h3 className="h6">Histórico recente</h3>
              <div className="vstack gap-3">
                {recentHistory.slice(0, 5).map((item) => (
                  <div key={item.snapshot_id}>
                    <div className="d-flex justify-content-between gap-2">
                      <strong className="small">{item.title}</strong>
                      <span className="badge text-bg-light">{item.hc_score.toFixed(1)}</span>
                    </div>
                    <small className="text-secondary">
                      {changeLabels[item.change_type] || item.change_type}
                      {' · '}{new Date(item.captured_at).toLocaleString('pt-BR')}
                    </small>
                  </div>
                ))}
                {recentHistory.length === 0 && <span className="text-secondary">Sem histórico recente.</span>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function CampaignDetails({ details, onClose }) {
  const { campaign, history, intelligence } = details;
  return (
    <>
      <div className="modal d-block" tabIndex="-1" role="dialog">
        <div className="modal-dialog modal-xl modal-dialog-scrollable">
          <div className="modal-content">
            <div className="modal-header">
              <div>
                <h2 className="modal-title h4">{campaign.title}</h2>
                <small>{campaign.company} · {typeLabels[campaign.campaign_type]}</small>
              </div>
              <button type="button" className="btn-close" onClick={onClose} aria-label="Fechar" />
            </div>
            <div className="modal-body">
              <div className="row g-4">
                <div className="col-lg-5">
                  <h3 className="h5">Análise atual</h3>
                  <p><strong>Recomendação:</strong> {recommendationLabels[intelligence.recommendation_level]}</p>
                  <p><strong>Confiança:</strong> {confidenceLabels[intelligence.confidence_level]}</p>
                  <p><strong>Posição histórica:</strong> {intelligence.historical_position}</p>
                  <p>{intelligence.recommendation_text}</p>
                  <ul>{intelligence.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                  {campaign.regulation_url && <a href={campaign.regulation_url} target="_blank" rel="noreferrer">Abrir regulamento</a>}
                </div>
                <div className="col-lg-7">
                  <h3 className="h5">Linha do tempo</h3>
                  <div className="list-group">
                    {history.map((snapshot) => (
                      <div className="list-group-item" key={snapshot.id}>
                        <div className="d-flex justify-content-between">
                          <strong>{changeLabels[snapshot.change_type] || snapshot.change_type}</strong>
                          <small>{new Date(snapshot.captured_at).toLocaleString('pt-BR')}</small>
                        </div>
                        <p className="mb-1">{snapshot.change_summary}</p>
                        <small>
                          {number.format(snapshot.bonus_points)} pontos ·
                          {' '}{snapshot.cost_status === 'unknown' ? 'Custo desconhecido' : money.format(snapshot.cost_brl)}
                        </small>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <div className="modal-footer"><button className="btn btn-secondary" onClick={onClose}>Fechar</button></div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop show" />
    </>
  );
}

function Stat({ title, value }) {
  return <div className="col-md-4 col-xl"><div className="card border-0 shadow-sm h-100"><div className="card-body"><div className="text-secondary small">{title}</div><div className="display-6 fw-bold">{value}</div></div></div></div>;
}
