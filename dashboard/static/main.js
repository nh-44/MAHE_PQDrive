async function loadReport() {
  const response = await fetch('/api/report');
  if (!response.ok) {
    throw new Error('Unable to load demo report');
  }
  return response.json();
}

function statCard(label, value, accent) {
  return `
    <article class="stat-card ${accent}">
      <span>${label}</span>
      <strong>${value}</strong>
    </article>
  `;
}

function renderThreatModel(model) {
  const entries = [
    ['Entry points', model.entry_points],
    ['Attack paths', model.attack_paths],
    ['Target systems', model.target_systems],
  ];
  return entries.map(([label, values]) => `
    <article class="info-card">
      <h3>${label}</h3>
      <ul>${values.map((item) => `<li>${item}</li>`).join('')}</ul>
    </article>
  `).join('');
}

function renderScenarios(scenarios) {
  return scenarios.map((scenario) => `
    <article class="scenario ${scenario.accepted ? 'pass' : 'fail'}">
      <div class="scenario-title">
        <h3>${scenario.name}</h3>
        <span>${scenario.accepted ? 'Accepted' : 'Blocked'}</span>
      </div>
      <p class="scenario-meta">Failed at: ${scenario.failed_at ?? 'none'} | Latency: ${scenario.duration_ms} ms</p>
      <pre>${JSON.stringify(scenario.result, null, 2)}</pre>
    </article>
  `).join('');
}

function renderMetrics(metrics) {
  return `
    <article class="metric-card">
      <h3>${metrics.scenario_count}</h3>
      <p>scenarios executed</p>
    </article>
    <article class="metric-card">
      <h3>${metrics.accepted_count}</h3>
      <p>accepted</p>
    </article>
    <article class="metric-card">
      <h3>${metrics.blocked_count}</h3>
      <p>blocked</p>
    </article>
    <article class="metric-card">
      <h3>${metrics.mean_latency_ms}</h3>
      <p>mean latency ms</p>
    </article>
  `;
}

async function refreshDashboard() {
  const report = await loadReport();

  document.querySelector('#stats').innerHTML = [
    statCard('Trusted charger token', report.policy.trusted_charger, 'accent-a'),
    statCard('Accepted scenarios', report.metrics.accepted_count, 'accent-b'),
    statCard('Blocked scenarios', report.metrics.blocked_count, 'accent-c'),
  ].join('');

  document.querySelector('#threatModel').innerHTML = renderThreatModel(report.threat_model);
  document.querySelector('#scenarioList').innerHTML = renderScenarios(report.scenarios);
  document.querySelector('#metrics').innerHTML = renderMetrics(report.metrics);
  document.querySelector('#recommendations').innerHTML = report.recommendations.map((item) => `<li>${item}</li>`).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  const refreshBtn = document.querySelector('#refreshBtn');
  refreshBtn.addEventListener('click', () => {
    refreshDashboard().catch((error) => {
      console.error(error);
      alert('Could not refresh demo report.');
    });
  });

  refreshDashboard().catch((error) => {
    console.error(error);
    document.body.insertAdjacentHTML('beforeend', '<div class="error-banner">Dashboard unavailable.</div>');
  });
});