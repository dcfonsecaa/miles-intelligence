import { useEffect, useMemo, useState } from 'react';
import { listCampaigns, runDemoScan, runLiveloScan } from './services/api';

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const number = new Intl.NumberFormat('pt-BR');
const typeLabels = {
  subscription: 'Adesão',
  upgrade: 'Upgrade',
  points_purchase: 'Compra de pontos',
  transfer_bonus: 'Transferência',
  card_acquisition: 'Aquisição de cartão',
  account_opening: 'Abertura de conta',
  insurance: 'Seguro',
  investment: 'Investimento',
  shopping: 'Shopping',
  travel: 'Viagem',
  other: 'Outro',
};
const modalityLabels = {
  monthly: 'Mensal',
  annual: 'Anual',
  one_time: 'Única',
  recurring: 'Recorrente',
  unknown: 'Não identificada',
};
const confidenceLabels = { high: 'Alta', medium: 'Média', low: 'Baixa' };
const confidenceClasses = { high: 'text-bg-success', medium: 'text-bg-warning', low: 'text-bg-secondary' };

export default function App() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  async function load() {
    setLoading(true);
    try {
      setCampaigns(await listCampaigns());
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function scanDemo() {
    setMessage('Executando varredura de demonstração...');
    try {
      const result = await runDemoScan();
      setMessage(`Varredura concluída: ${result.inserted} nova(s), ${result.duplicates} já conhecida(s).`);
      await load();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function scanLivelo() {
    setMessage('Consultando regulamentos oficiais da Livelo...');
    try {
      const result = await runLiveloScan();
      setMessage(`Livelo consultada: ${result.inserted} nova(s), ${result.duplicates} já conhecida(s).`);
      await load();
    } catch (error) {
      setMessage(error.message);
    }
  }

  useEffect(() => { load(); }, []);

  const stats = useMemo(() => {
    const financiallyAssessed = campaigns.filter((item) => item.cost_status !== 'unknown');
    return {
      total: campaigns.length,
      assessed: financiallyAssessed.length,
      average: financiallyAssessed.length
        ? financiallyAssessed.reduce((sum, item) => sum + item.hc_score, 0) / financiallyAssessed.length
        : null,
    };
  }, [campaigns]);

  return (
    <main className="min-vh-100 bg-light">
      <header className="hero text-white py-5">
        <div className="container py-3">
          <span className="badge text-bg-warning mb-3">Radar HC · Model V2</span>
          <h1 className="display-5 fw-bold">Miles Intelligence</h1>
          <p className="lead col-lg-8 mb-4">Campanhas normalizadas para análise histórica e inteligência financeira.</p>
          <div className="d-flex flex-wrap gap-2">
            <button className="btn btn-light btn-lg" onClick={scanLivelo}>Consultar Livelo</button>
            <button className="btn btn-outline-light btn-lg" onClick={scanDemo}>Rodar demonstração</button>
          </div>
        </div>
      </header>

      <section className="container-fluid px-4 py-5">
        {message && <div className="alert alert-info">{message}</div>}
        <div className="row g-3 mb-4">
          <Stat title="Campanhas monitoradas" value={number.format(stats.total)} />
          <Stat title="Custos avaliados" value={number.format(stats.assessed)} />
          <Stat title="HC Score médio confirmado" value={stats.average === null ? 'Não calculado' : stats.average.toFixed(1)} />
        </div>

        <div className="card border-0 shadow-sm">
          <div className="card-body p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h2 className="h4 mb-0">Campanhas normalizadas</h2>
              <button className="btn btn-outline-dark btn-sm" onClick={load}>Atualizar</button>
            </div>
            {loading ? <p>Carregando...</p> : campaigns.length === 0 ? (
              <p className="text-secondary mb-0">Nenhuma campanha salva. Execute a primeira varredura.</p>
            ) : (
              <div className="table-responsive">
                <table className="table align-middle">
                  <thead>
                    <tr>
                      <th>Empresa</th><th>Campanha</th><th>Tipo</th><th>Modalidade</th>
                      <th>Pontos totais</th><th>Duração</th><th>Pontos/mês</th>
                      <th>Custo</th><th>Situação</th><th>CPM</th><th>Confiança</th><th>Regulamento</th>
                    </tr>
                  </thead>
                  <tbody>{campaigns.map((item) => (
                    <tr key={item.id}>
                      <td className="fw-semibold">{item.company}</td>
                      <td><div>{item.title}</div><small className="text-secondary">{item.category}</small></td>
                      <td><span className="badge text-bg-primary">{typeLabels[item.campaign_type] || item.campaign_type}</span></td>
                      <td>{modalityLabels[item.modality] || item.modality}</td>
                      <td>{number.format(item.bonus_points)}</td>
                      <td>{item.duration_months ? `${item.duration_months} meses` : 'Não identificada'}</td>
                      <td>{item.monthly_points === null ? 'Não calculado' : number.format(item.monthly_points)}</td>
                      <td>{item.cost_status === 'unknown' ? 'Custo desconhecido' : money.format(item.cost_brl)}</td>
                      <td>{item.cost_status === 'known' ? 'Confirmado' : item.cost_status === 'estimated' ? 'Estimado' : 'Desconhecido'}</td>
                      <td>{item.cpm === null ? 'Não calculado' : money.format(item.cpm)}</td>
                      <td>
                        <span className={`badge ${confidenceClasses[item.extraction_confidence] || 'text-bg-secondary'}`}>
                          {confidenceLabels[item.extraction_confidence] || item.extraction_confidence}
                        </span>
                      </td>
                      <td>
                        {item.regulation_url
                          ? <a href={item.regulation_url} target="_blank" rel="noreferrer">Abrir</a>
                          : 'Indisponível'}
                      </td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

function Stat({ title, value }) {
  return <div className="col-md-4"><div className="card border-0 shadow-sm h-100"><div className="card-body"><div className="text-secondary small">{title}</div><div className="display-6 fw-bold">{value}</div></div></div></div>;
}
