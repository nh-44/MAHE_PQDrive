/* ===== Notification System ===== */
class NotificationManager {
  constructor() {
    this.container = document.querySelector('#notificationContainer');
  }

  show(type, title, message, duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const icon = this.getIcon(type);
    notification.innerHTML = `
      <div class="notification-icon">${icon}</div>
      <div class="notification-content">
        <div class="notification-title">${title}</div>
        <div class="notification-message">${message}</div>
      </div>
      <button class="notification-close">✕</button>
    `;
    
    this.container.appendChild(notification);
    
    // Close button handler
    notification.querySelector('.notification-close').addEventListener('click', () => {
      this.remove(notification);
    });
    
    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => this.remove(notification), duration);
    }
  }

  getIcon(type) {
    const icons = {
      threat: '⚠️',
      success: '✓',
      warning: '⚡',
      info: 'ℹ️'
    };
    return icons[type] || '●';
  }

  remove(notification) {
    notification.classList.add('removing');
    setTimeout(() => notification.remove(), 300);
  }

  threat(title, message) {
    this.show('threat', title, message, 6000);
  }

  success(title, message) {
    this.show('success', title, message, 4000);
  }

  warning(title, message) {
    this.show('warning', title, message, 5000);
  }

  info(title, message) {
    this.show('info', title, message, 3000);
  }
}

// Initialize notification manager
const notifications = new NotificationManager();

/* ===== API Functions ===== */
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
    
    // Show notifications based on result
    if (threatInjection && threatInjection !== 'clear') {
      // Threat was injected
      const threatMap = {
        'bit-flip': 'Bit-Flip Attack',
        'downgrade': 'Version Downgrade Attack',
        'tamper-signature': 'Signature Tampering Attack'
      };
      const threatName = threatMap[threatInjection] || threatInjection;
      
      if (!result.accepted) {
        // Threat was detected and blocked
        notifications.threat(
          `🛡️ THREAT BLOCKED: ${threatName}`,
          `The ${threatName} was detected and successfully blocked. Vehicle remains secure.`
        );
      } else {
        // Threat was NOT detected (system failed to block)
        notifications.warning(
          `⚠️ THREAT UNDETECTED: ${threatName}`,
          `WARNING: A ${threatName} was injected but NOT detected! System security compromised.`
        );
      }
    } else if (!result.accepted) {
      // Attack scenario detected
      const reasonMap = {
        'anti_juice': 'Anti-Juice Jacking',
        'replay': 'Replay Attack',
        'tamper_signature': 'Signature Tampering',
        'rollback': 'Rollback Attack',
        'version': 'Version Rollback',
        'dilithium': 'Invalid Signature'
      };
      const reason = reasonMap[result.failed_at] || result.failed_at || 'Security Threat';
      
      notifications.threat(
        `🛡️ ATTACK DETECTED: ${reason}`,
        `Attack scenario blocked at: ${result.failed_at || 'verification'}. Vehicle protected.`
      );
    } else {
      // Legitimate update accepted
      notifications.success(
        '✓ UPDATE ACCEPTED',
        `${scenarioName} passed all security checks. Firmware is authentic and safe.`
      );
    }
    
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

    // Display chain-of-thought logs
    if (result.chain_of_thought) {
      renderChainOfThought(result.chain_of_thought, result.scenario_logs);
    }

  } catch (error) {
    console.error('Error running scenario:', error);
    alert(`Error running scenario: ${error.message}`);
  }
}

function renderChainOfThought(chainText, logs) {
  const logsDiv = document.querySelector('#chainLogs');
  const explainerDiv = document.querySelector('#cryptoExplainer');
  
  if (!logs || logs.length === 0) {
    logsDiv.innerHTML = '<div class="chain-logs empty">No logs available</div>';
    return;
  }

  // Render detailed logs
  let logsHtml = '';
  logs.forEach(log => {
    const stage = log.stage.toLowerCase();
    logsHtml += `
      <div class="log-entry ${stage}">
        <div class="log-timestamp">${log.elapsed_ms.toFixed(2)}ms</div>
        <div class="log-stage">${log.stage}</div>
        <div class="log-message">${log.message}</div>
      </div>
    `;
  });
  logsDiv.innerHTML = logsHtml;

  // Render crypto principles explanation
  const cryptoPrinciples = {
    'kyber_kem': {
      title: 'Kyber Key Encapsulation (Post-Quantum Safe)',
      desc: 'Establishes quantum-resistant shared secret using lattice-based cryptography. Kyber is NIST-standardized and protects against both classical and quantum attacks.'
    },
    'dilithium_signature': {
      title: 'Dilithium Digital Signature (Post-Quantum Safe)',
      desc: 'Verifies firmware origin and integrity using lattice-based signatures. Prevents code injection and man-in-the-middle attacks.'
    },
    'sha3_hash': {
      title: 'SHA3-256 Integrity Check (Quantum-Resistant)',
      desc: 'Provides cryptographic proof that firmware hasn\'t been tampered with. Detects bit-flip attacks and data corruption.'
    },
    'replay_defense': {
      title: 'Replay Attack Prevention (Nonce-Based)',
      desc: 'Ensures OTA updates can\'t be repeated. Each update has a unique identifier that\'s recorded and checked.'
    },
    'version_monotonicity': {
      title: 'Rollback Prevention (Version Checking)',
      desc: 'Blocks attempts to install older firmware versions. Prevents attackers from exploiting known vulnerabilities.'
    },
    'vehicle_state_gating': {
      title: 'Vehicle Safety Gating (Context-Aware)',
      desc: 'Blocks OTA updates when vehicle is moving, charging, or in thermal stress. Prevents update failures and data corruption.'
    }
  };

  let explainerHtml = '<h3>🔐 Cryptographic Principles Used</h3>';
  Object.values(cryptoPrinciples).forEach(principle => {
    explainerHtml += `
      <div class="crypto-principle">
        <div class="principle-title">${principle.title}</div>
        <div class="principle-desc">${principle.desc}</div>
      </div>
    `;
  });
  
  explainerDiv.innerHTML = explainerHtml;
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
  
  // Fetch and render audit log
  try {
    const auditResponse = await fetch('/api/audit-log');
    if (auditResponse.ok) {
      const auditLog = await auditResponse.json();
      document.querySelector('#auditTimeline').innerHTML = renderAuditTimeline(auditLog);
    }
  } catch (error) {
    console.error('Error loading audit log:', error);
  }
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
    });
  });

  // Simulate button handler
  const simulateBtn = document.querySelector('#simulateBtn');
  if (simulateBtn) {
    simulateBtn.addEventListener('click', () => {
      const activeScenario = document.querySelector('.scenario-btn.active');
      if (!activeScenario) {
        alert('Please select a scenario first');
        return;
      }
      runScenario(activeScenario.dataset.scenario).catch((error) => {
        console.error('Scenario execution error:', error);
      });
    });
  }

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

  // Setup collapsible sections
  function setupCollapsibles() {
    const threatModelHeader = document.querySelector('#threatModelHeader');
    const scenarioHeader = document.querySelector('#scenarioHeader');
    
    if (threatModelHeader) {
      threatModelHeader.addEventListener('click', () => {
        threatModelHeader.classList.toggle('active');
        const content = threatModelHeader.nextElementSibling;
        if (content) {
          content.classList.toggle('visible');
          content.classList.toggle('hidden');
        }
      });
    }
    
    if (scenarioHeader) {
      scenarioHeader.addEventListener('click', () => {
        scenarioHeader.classList.toggle('active');
        const content = scenarioHeader.nextElementSibling;
        if (content) {
          content.classList.toggle('visible');
          content.classList.toggle('hidden');
        }
      });
    }
  }
  
  // Initialize collapsibles
  setupCollapsibles();

  refreshDashboard().catch((error) => {
    console.error(error);
    document.body.insertAdjacentHTML('beforeend', '<div class="error-banner">Dashboard unavailable.</div>');
  });
});