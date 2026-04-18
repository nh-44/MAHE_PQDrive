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

function getVehicleState() {
  return {
    speed_kph: parseInt(document.querySelector('#speed')?.value || 0),
    battery_soc: parseInt(document.querySelector('#battery')?.value || 68),
    temperature_c: parseInt(document.querySelector('#temperature')?.value || 31),
    data_link_locked: document.querySelector('#dataLocked')?.checked ?? true,
    charging_active: document.querySelector('#charging')?.checked ?? true,
    thermal_state: 'normal',
  };
}

function formatDetailItem(label, value) {
  if (typeof value === 'object') {
    value = JSON.stringify(value);
  }
  return `
    <div class="detail-item">
      <div class="label">${label}</div>
      <div class="value">${value}</div>
    </div>
  `;
}

async function runScenario(scenarioName) {
  const vehicleState = getVehicleState();
  
  try {
    const response = await fetch('/api/run-scenario', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_name: scenarioName, vehicle_state: vehicleState }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();
    
    // Display result
    const resultDiv = document.querySelector('#runResult');
    const status = result.accepted ? 'accepted' : 'blocked';
    const failedAt = result.failed_at ? `Failed at: ${result.failed_at}` : 'All checks passed';
    
    let detailsHtml = `
      ${formatDetailItem('Status', status.toUpperCase())}
      ${formatDetailItem('Latency', `${result.duration_ms} ms`)}
      ${formatDetailItem('Reason', failedAt)}
      ${formatDetailItem('Vehicle Speed', `${vehicleState.speed_kph} km/h`)}
      ${formatDetailItem('Battery SOC', `${vehicleState.battery_soc}%`)}
      ${formatDetailItem('Temperature', `${vehicleState.temperature_c}°C`)}
      ${formatDetailItem('Data-line Locked', vehicleState.data_link_locked ? 'Yes' : 'No')}
      ${formatDetailItem('Charging Active', vehicleState.charging_active ? 'Yes' : 'No')}
    `;

    document.querySelector('#resultName').textContent = scenarioName;
    document.querySelector('#resultStatus').textContent = status.toUpperCase();
    document.querySelector('#resultStatus').parentElement.className = `result-status ${status}`;
    document.querySelector('#resultLatency').textContent = `${result.duration_ms} ms`;
    document.querySelector('#resultDetails').innerHTML = detailsHtml;
    resultDiv.classList.remove('hidden');

  } catch (error) {
    console.error('Error running scenario:', error);
    alert(`Error running scenario: ${error.message}`);
  }
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
  // Range slider display updates
  const speedSlider = document.querySelector('#speed');
  if (speedSlider) {
    speedSlider.addEventListener('input', (e) => {
      document.querySelector('#speedValue').textContent = e.target.value;
    });
  }

  const batterySlider = document.querySelector('#battery');
  if (batterySlider) {
    batterySlider.addEventListener('input', (e) => {
      document.querySelector('#batteryValue').textContent = e.target.value;
    });
  }

  const tempSlider = document.querySelector('#temperature');
  if (tempSlider) {
    tempSlider.addEventListener('input', (e) => {
      document.querySelector('#tempValue').textContent = e.target.value;
    });
  }

  // Scenario button handlers
  document.querySelectorAll('.scenario-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.scenario-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      runScenario(btn.dataset.scenario).catch((error) => {
        console.error('Scenario execution error:', error);
      });
    });
  });

  // Refresh button
  const refreshBtn = document.querySelector('#refreshBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      refreshDashboard().catch((error) => {
        console.error(error);
        alert('Could not refresh demo report.');
      });
    });
  }

  refreshDashboard().catch((error) => {
    console.error(error);
    document.body.insertAdjacentHTML('beforeend', '<div class="error-banner">Dashboard unavailable.</div>');
  });
});