import { useEffect, useState } from 'react';
import {
  getCampaignHistory,
  getCampaignIntelligence,
  getIntelligenceHighlights,
  listCampaigns,
  recalculateIntelligence,
  runEsferaScan,
  runDemoScan,
  runLiveloScan,
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

export default function App() {
  const [campaigns, setCampaigns] = useState([]);
  const [highlights, setHighlights] = useState(emptyHighlights);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [details, setDetails] = useState(null);
  const [sourceFilter, setSourceFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');

  async function load() {
    setLoading(true);
    try {
      const [items, summary] = await Promise.all([listCampaigns(), getIntelligenceHighlights()]);
      const enriched = await Promise.all(items.map(async (campaign) => ({
        ...campaign,
        intelligence: await getCampaignIntelligence(campaign.id),
      })));
      setCampaigns(enriched);
      setHighlights(summary);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function runScan(kind) {
    const sourceLabels = { livelo: 'Livelo', esfera: 'Esfera', smiles: 'Smiles' };
    setMessage(sourceLabels[kind]
      ? `Consultando a fonte oficial da ${sourceLabels[kind]}...`
      : 'Executando demonstração...');
    try {
      const scans = {
        livelo: runLiveloScan,
        esfera: runEsferaScan,
        smiles: runSmilesScan,
        demo: runDemoScan,
      };
      const result = await scans[kind]();
      const source = result.source ? ` (${result.source})` : '';
      setMessage(
        `Coleta concluída${source}: ${result.inserted} nova(s), ${result.updated} alterada(s), `
        + `${result.unchanged} sem mudança e ${result.errors} erro(s).`,
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
  ));

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
            <button className="btn btn-outline-light btn-lg" onClick={() => runScan('demo')}>Rodar demonstração</button>
            <button className="btn btn-outline-warning btn-lg" onClick={recalculate}>Recalcular análises</button>
          </div>
        </div>
      </header>

      <section className="container-fluid px-4 py-5">
        {message && <div className="alert alert-info">{message}</div>}
        <div className="row g-3 mb-4">
          {['Livelo', 'Esfera', 'Smiles'].map((source) => (
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
                  aria-label="Filtrar por fonte"
                  value={sourceFilter}
                  onChange={(event) => setSourceFilter(event.target.value)}
                >
                  <option value="all">Todas as fontes</option>
                  <option value="Livelo">Livelo</option>
                  <option value="Esfera">Esfera</option>
                  <option value="Smiles">Smiles</option>
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
