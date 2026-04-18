async function loadReport() {
  const response = await fetch('/api/report');
  if (!response.ok) {
    throw new Error('Unable to load demo report');
  }
  return response.json();
}

async function loadPresets() {
  const response = await fetch('/api/presets');
  if (!response.ok) {
    throw new Error('Unable to load presets');
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

function loadPresetState(presetName, presets) {
  const presetState = presets[presetName];
  if (!presetState) return;
  
  document.querySelector('#speed').value = presetState.speed_kph || 0;
  document.querySelector('#speedValue').textContent = presetState.speed_kph || 0;
  
  document.querySelector('#battery').value = presetState.battery_soc || 68;
  document.querySelector('#batteryValue').textContent = presetState.battery_soc || 68;
  
  document.querySelector('#temperature').value = presetState.temperature_c || 31;
  document.querySelector('#tempValue').textContent = presetState.temperature_c || 31;
  
  document.querySelector('#dataLocked').checked = presetState.data_link_locked !== false;
  document.querySelector('#charging').checked = presetState.charging_active !== false;
}

function renderAuditTimeline(auditLog) {
  if (!auditLog || auditLog.length === 0) {
    return '<div class="timeline-empty">No audit events recorded</div>';
  }
  
  return auditLog.map((event, idx) => `
    <div class="timeline-item">
      <div class="timeline-marker"></div>
      <div class="timeline-content">
        <div class="timeline-title">${event.event_type || event.event}</div>
        <div class="timeline-time">${event.timestamp}</div>
        <div class="timeline-detail">${JSON.stringify(event.details || event.message || event).substring(0, 100)}</div>
      </div>
    </div>
  `).join('');
}

async function runScenario(scenarioName) {
  const vehicleState = getVehicleState();
  const threatInjection = document.querySelector('[data-threat-selected]')?.getAttribute('data-threat-selected');
  
  try {
    const payload = {
      scenario_name: scenarioName,
      vehicle_state: vehicleState,
    };
    if (threatInjection && threatInjection !== 'clear') {
      payload.threat_injection = threatInjection;
    }

    const response = await fetch('/api/run-scenario', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
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
    
    if (result.threat_injected) {
      detailsHtml += formatDetailItem('Threat Injected', result.threat_injected);
    }

    document.querySelector('#resultName').textContent = scenarioName;
    document.querySelector('#resultStatus').textContent = status.toUpperCase();
    document.querySelector('#resultStatus').parentElement.className = `result-status ${status}`;
    document.querySelector('#resultLatency').textContent = `${result.duration_ms} ms`;
    document.querySelector('#resultDetails').innerHTML = detailsHtml;
    resultDiv.classList.remove('hidden');
    
    // Update audit timeline
    if (result.audit_log) {
      document.querySelector('#auditTimeline').innerHTML = renderAuditTimeline(result.audit_log);
    }

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
  // Load and render presets
  loadPresets().then((presets) => {
    const presetsContainer = document.querySelector('#presetButtons');
    presetsContainer.innerHTML = Object.keys(presets).map((name) => 
      `<button class="preset-btn" data-preset="${name}">${name}</button>`
    ).join('');
    
    // Preset button handlers
    document.querySelectorAll('.preset-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.preset-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        loadPresetState(btn.dataset.preset, presets);
      });
    });
  }).catch((error) => console.error('Could not load presets:', error));
  
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

  // Threat injection button handlers
  document.querySelectorAll('.threat-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const threatType = btn.dataset.threat;
      if (threatType === 'clear') {
        document.querySelectorAll('.threat-btn').forEach((b) => b.classList.remove('active'));
        document.querySelector('[data-threat-selected]')?.removeAttribute('data-threat-selected');
        document.querySelector('#threatStatus').innerHTML = '';
      } else {
        document.querySelectorAll('.threat-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.threat-btn').forEach((b) => b.removeAttribute('data-threat-selected'));
        btn.setAttribute('data-threat-selected', threatType);
        const threatNames = {
          'bit-flip': 'Firmware corruption',
          'downgrade': 'Version downgrade',
          'tamper-signature': 'Signature tampering',
        };
        document.querySelector('#threatStatus').innerHTML = `<div class="threat-active">Threat injected: ${threatNames[threatType]}</div>`;
      }
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