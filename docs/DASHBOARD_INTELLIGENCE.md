# Dashboard Intelligence

`GET /api/intelligence/dashboard` fornece a visão consolidada consumida pela
página inicial:

- melhor campanha detectada no dia;
- ranking das dez maiores campanhas por HC Score;
- dez eventos mais recentes do histórico;
- data da última atualização;
- programas disponíveis para filtro.

O parâmetro opcional `program` limita ranking, melhor campanha e histórico sem
alterar os dados persistidos. No frontend, os cartões de ranking exibem o HC
Score e abrem a análise detalhada da campanha.

Se não houver campanha detectada no dia ou histórico disponível, o dashboard
apresenta estados vazios explícitos. Collectors, cálculos e rotas existentes
permanecem inalterados.
