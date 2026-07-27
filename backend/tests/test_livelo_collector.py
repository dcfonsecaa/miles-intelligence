from app.services.livelo_collector import parse_livelo_campaigns


HTML_FIXTURE = """
<html><body>
  <h2>[COMPRA DE PONTOS] PASSAGEIRO DE PRIMEIRA - 52% OFF + 5% OFF no Pix</h2>
  <p>Período 24/07/2026 - 26/07/2026</p>
  <p><a href="/regulamento/compra-pontos">Conferir regulamento</a></p>

  <h3>[ADESÃO] Mega - 74k pts extras em 12 m - mensal / 78k pts extras em 12 m - anual</h3>
  <p>Período: 24/07/2026 a 27/07/2026</p>
  <a href="https://assets.example.com/mega.pdf">Conferir regulamento</a>

  <h4>Benefícios aos assinantes do Clube Livelo</h4>
  <a href="/regulamento/permanente">Regulamento novo</a>
</body></html>
"""


def test_parser_extracts_promotional_campaigns():
    campaigns = parse_livelo_campaigns(HTML_FIXTURE)

    assert len(campaigns) == 2
    assert campaigns[0].company == "Livelo"
    assert campaigns[0].source_url == "https://www.livelo.com.br/regulamento/compra-pontos"
    assert campaigns[1].bonus_points == 78_000
    assert "24/07/2026" in campaigns[1].summary


def test_parser_ignores_permanent_non_promotional_rules():
    campaigns = parse_livelo_campaigns(HTML_FIXTURE)
    assert all("Benefícios aos assinantes" not in item.title for item in campaigns)
