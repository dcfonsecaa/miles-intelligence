import { useEffect, useMemo, useState } from 'react';
import { listCampaigns, runDemoScan, runLiveloScan } from './services/api';

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const number = new Intl.NumberFormat('pt-BR');

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

  const stats = useMemo(() => ({
    total: campaigns.length,
    exceptional: campaigns.filter((item) => item.hc_score >= 80).length,
    average: campaigns.length ? campaigns.reduce((sum, item) => sum + item.hc_score, 0) / campaigns.length : 0,
  }), [campaigns]);

  return (
    <main className="min-vh-100 bg-light">
      <header className="hero text-white py-5">
        <div className="container py-3">
          <span className="badge text-bg-warning mb-3">Radar HC · MVP</span>
          <h1 className="display-5 fw-bold">Miles Intelligence</h1>
          <p className="lead col-lg-8 mb-4">Detector de campanhas anormais, custo por milheiro e oportunidades excepcionais.</p>
          <div className="d-flex flex-wrap gap-2">
            <button className="btn btn-light btn-lg" onClick={scanLivelo}>Consultar Livelo</button>
            <button className="btn btn-outline-light btn-lg" onClick={scanDemo}>Rodar demonstração</button>
          </div>
        </div>
      </header>

      <section className="container py-5">
        {message && <div className="alert alert-info">{message}</div>}
        <div className="row g-3 mb-4">
          <Stat title="Campanhas monitoradas" value={number.format(stats.total)} />
          <Stat title="Oportunidades excepcionais" value={number.format(stats.exceptional)} />
          <Stat title="HC Score médio" value={stats.average.toFixed(1)} />
        </div>

        <div className="card border-0 shadow-sm">
          <div className="card-body p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h2 className="h4 mb-0">Oportunidades detectadas</h2>
              <button className="btn btn-outline-dark btn-sm" onClick={load}>Atualizar</button>
            </div>
            {loading ? <p>Carregando...</p> : campaigns.length === 0 ? (
              <p className="text-secondary mb-0">Nenhuma campanha salva. Execute a primeira varredura.</p>
            ) : (
              <div className="table-responsive">
                <table className="table align-middle">
                  <thead><tr><th>Empresa</th><th>Campanha</th><th>Pontos</th><th>Custo</th><th>CPM</th><th>HC Score</th><th>Anomalia</th></tr></thead>
                  <tbody>{campaigns.map((item) => (
                    <tr key={item.id}>
                      <td className="fw-semibold">{item.company}</td>
                      <td><div>{item.title}</div><small className="text-secondary">{item.category}</small></td>
                      <td>{number.format(item.bonus_points)}</td>
                      <td>{money.format(item.cost_brl)}</td>
                      <td>{item.cpm === null ? '—' : money.format(item.cpm)}</td>
                      <td><span className={`badge ${item.hc_score >= 80 ? 'text-bg-success' : item.hc_score >= 60 ? 'text-bg-warning' : 'text-bg-secondary'}`}>{item.hc_score}</span></td>
                      <td>{item.anomaly_score}</td>
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
