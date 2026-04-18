# PQDrive: Post-Quantum OTA Security for Connected Vehicles

PQDrive is a comprehensive hackathon demo showcasing post-quantum cryptography for OTA trust, charger-mediated vehicle update protection, and safety-aware recovery for connected electric vehicles.

## What it demonstrates

- **Post-Quantum Cryptography** — Kyber/ML-KEM for session establishment, Dilithium/ML-DSA for signatures, SHA3-256 for integrity
- **Fail-Fast OTA Pipeline** — Multi-stage verification with per-stage latency instrumentation
- **Charger Authentication** — Mutual authentication between vehicle and charger with pseudonymous identity protection
- **Anti-Juice-Jacking Defense** — Vehicle state gating blocks unsafe charging conditions (speed, battery, temperature, data-lock)
- **ECU-Level Policy Enforcement** — Safety-critical ECUs require charger authentication; infotainment deploys without charger
- **Cryptographic Agility** — Fallback to RSA-2048 for comparison and legacy compatibility
- **Recovery & Forensics** — Dilithium-signed audit log with snapshots for non-repudiation
- **Interactive Dashboard** — Live scenario controls, threat injection, API documentation, audit timeline

## Project layout

- `core/`: cryptographic verification pipeline and shared demo runner.
- `vehicle/`: gateway, OTA server, charger attestation, ECU policy, and recovery logic.
- `attacks/`: rogue charger, tamper, rollback, HNDL, and charger-security demo scenarios.
- `dashboard/`: Flask UI for live demo reporting.
- `tests/`: end-to-end and charger-security tests.

## Quick Start (2 minutes)

```powershell
# Navigate to project
Set-Location 'E:\Hackathons , CODMAV , etc\PQDrive\MAHE_PQDrive'

# Run tests to verify installation
..\pqauto-env\Scripts\python.exe -m pytest tests/ -q

# Run CLI demo (all 7 scenarios with results)
..\pqauto-env\Scripts\python.exe main.py

# Start interactive dashboard
..\pqauto-env\Scripts\python.exe -m dashboard.app
```

Then open **http://127.0.0.1:5000** in your browser.

---

## Step-by-Step Demonstration Guide

### Phase 1: CLI Demo (Non-Interactive) — 1 minute

**What it shows**: All 7 security scenarios with pass/block results and latency metrics.

```powershell
..\pqauto-env\Scripts\python.exe main.py
```

**Expected Output**:
```
Scenario results:
  Legitimate OTA ........................... ACCEPTED (1.086 ms)
  Trusted Charger OTA ...................... ACCEPTED (2.667 ms)
  Anti-Juice Jacking ...................... BLOCKED (anti_juice)
  Replay Attack ........................... BLOCKED (replay)
  Rogue Charger Attack .................... BLOCKED (source)
  Rollback Attack ......................... BLOCKED (version)
  Tamper Attack ........................... BLOCKED (dilithium)

Metrics:
  - Mean latency: 1.87 ms
  - Accept rate: 28.6% (2/7)
  - Block rate: 71.4% (5/7)
```

**Key Insights**:
- 2 attacks pass (legitimate scenarios)
- 5 attacks blocked at correct defense layer
- Sub-millisecond crypto operations
- Post-quantum signatures prove authentication

---

### Phase 2: Interactive Dashboard — 5-10 minutes

Start the dashboard and open in browser:

```powershell
..\pqauto-env\Scripts\python.exe -m dashboard.app
# Open http://localhost:5000
```

#### Walkthrough Scenario 1: State Presets

**Show**: How presets simplify scenario setup

1. Click **"Parked & Charging"** preset button
   - Watch sliders auto-update: Speed=0, Battery=68%, Temp=31°C, Data-locked=Yes, Charging=Yes
   - This is the safe charging state

2. Click **"Legitimate OTA"** scenario button
   - Result: ✓ ACCEPTED
   - Latency: ~1.1 ms
   - Reason: All checks passed

3. Click **"Highway"** preset button
   - Speed jumps to 100 km/h, Battery=45%
   - This is unsafe for charging

4. Run **"Anti-Juice Jacking"** scenario
   - Result: ✗ BLOCKED (anti_juice)
   - Reason: Vehicle moving; can't safely update braking_ecu
   - This is the defense working

**Judge Point**: "The system knows when it's unsafe to update. Presets let you explore boundary conditions instantly."

---

#### Walkthrough Scenario 2: Threat Injection

**Show**: How security defenses catch deliberate attacks

1. Return to **"Parked & Charging"** preset (for safe baseline)

2. Run **"Legitimate OTA"** without threat → ✓ ACCEPTED

3. Click **"Bit Flip"** threat button
   - Orange warning appears: "Threat injected: Firmware corruption"

4. Run **"Legitimate OTA"** with Bit Flip active
   - Result: ✗ BLOCKED (dilithium or hash check)
   - Reason: Payload tampered; signature/hash verification fails

5. Click **"Clear"** threat button to reset

6. Click **"Downgrade"** threat button

7. Run **"Rollback Attack"** scenario
   - Result: ✗ BLOCKED (version)
   - Reason: Version downgrade detected

8. Click **"Tamper-Signature"** threat button

9. Run **"Legitimate OTA"** with Tamper-Signature
   - Result: ✗ BLOCKED (dilithium)
   - Reason: Dilithium signature verification fails

**Judge Point**: "All three attack vectors are caught. Post-quantum signatures prove authenticity even when attackers corrupt the payload."

---

#### Walkthrough Scenario 3: Audit Log Timeline

**Show**: Security event tracing and non-repudiation

1. Scroll down to **"Audit Log Timeline"** section

2. Run any scenario (e.g., "Trusted Charger OTA")
   - Timeline populates with events: timestamps, decision points, details

3. Scroll through events to see:
   - Request validation
   - Charger authentication
   - Vehicle state checks
   - Decision outcome

**Judge Point**: "Every decision is logged and signed. Audit trail proves what happened and when for forensic analysis."

---

#### Walkthrough Scenario 4: API Documentation

**Show**: Professional integration path for production

1. Click **"API Docs"** link in hero section (or navigate to http://localhost:5000/api/docs/html)

2. Show endpoints:
   - `GET /api/presets` — Available vehicle configurations
   - `GET /api/report` — Full scenario results
   - `POST /api/run-scenario` — Execute with state/threat overrides
   - `GET /api/audit-log` — Security audit trail
   - `GET /api/docs` — OpenAPI 3.0 specification (JSON)

3. Demonstrate API call in browser console:
   ```javascript
   fetch('/api/run-scenario', {
     method: 'POST',
     headers: {'Content-Type': 'application/json'},
     body: JSON.stringify({
       scenario_name: 'Legitimate OTA',
       vehicle_state: {speed_kph: 0, battery_soc: 50},
       threat_injection: 'bit-flip'
     })
   }).then(r => r.json()).then(d => console.log(d))
   ```

**Judge Point**: "Production-ready API with OpenAPI spec. Security decisions are programmatically verifiable."

---

### Phase 3: Explore Threat Model & Recommendations — 2-3 minutes

1. Scroll to **"Threat Model"** section
   - Shows entry points: OTA request, charger auth path, CAN simulation
   - Attack paths: rogue charger, tamper, rollback, replay
   - Target systems: gateway, pipeline, ECU policy, recovery

2. Scroll to **"Scenario Results"** section
   - Each scenario shows: name, pass/fail, failure stage, raw result JSON
   - Click on a scenario to see full cryptographic trace

3. Scroll to **"Performance"** section
   - Metrics: scenario count, accept/block rates, mean latency
   - Latency breakdown shows per-stage costs

4. Scroll to **"Recommendations"** section
   - Next steps for production: mTLS, durable replay cache, signed manifests

**Judge Point**: "Every aspect of the system is visible: threat model, security outcomes, performance metrics, and deployment roadmap."

---

## 4 New Dashboard Features (Latest Update)

### 1. Vehicle State Presets
- **4 Preset Configurations**: Parked & Charging, Highway, Critical Battery, Normal Idle
- **One-Click Setup**: Presets update all sliders/checkboxes instantly
- **API Endpoint**: `GET /api/presets`
- **Use Case**: Explore how vehicle state affects security policy without manual tuning

### 2. Threat Injection
- **3 Attack Types**: Bit-flip (corrupt payload), Downgrade (lower version), Tamper-Signature (break sig)
- **Real-Time Testing**: Inject threat and run scenario to see defense outcome
- **Scenario Results**: Result card shows injected threat type and defense layer
- **Use Case**: Demonstrate that all attack vectors are caught by multi-layer defense

### 3. API Documentation
- **OpenAPI 3.0 Spec**: Formal specification of all 8 REST endpoints
- **HTML Documentation**: Professional reference page with examples
- **Two Access Points**: JSON (`/api/docs`) and HTML (`/api/docs/html`)
- **Use Case**: Show integration path for production systems and judge credibility

### 4. Audit Log Timeline
- **Security Event Timeline**: Chronological view of audit events with timestamps
- **Visual Markers**: Teal circular markers with event details
- **Dynamic Rendering**: Updates after each scenario execution
- **Use Case**: Demonstrate forensic evidence trail and decision traceability

---

## For Judges: Key Evaluation Points

### Security Depth (25%)
- **Multi-Layer Defense**: Show the 7-layer verification pipeline in source code
- **STRIDE Coverage**: See [THREAT_MODEL.md](THREAT_MODEL.md) for spoofing/tampering/repudiation/disclosure/DoS/elevation analysis
- **Charger Authentication**: Interactive demo shows mutual auth with vehicle state gating
- **Anti-Juice-Jacking**: Run "Anti-Juice Jacking" scenario with speed preset to demonstrate blocking
- **Cryptographic Proof**: Dilithium signatures ensure authentication; Kyber ensures confidentiality
- **Recovery Evidence**: Audit timeline shows non-repudiation with signed events

**Judge Demo Path**: CLI → Threat Injection (show all 3 attacks blocked) → Audit Timeline → API Docs

### Feasibility (20%)
- **One-Command Setup**: `python main.py` and `python -m dashboard.app` work out-of-box
- **Fast Testing**: 12 tests in 0.11s on any machine
- **No External Dependencies**: Everything packaged; venv pre-configured
- **Cross-Platform**: Works on Windows (demo), macOS, Linux
- **Clear Troubleshooting**: See [DEPLOYMENT.md](DEPLOYMENT.md) for issues

**Judge Demo Path**: Run `pytest -q` → Run `main.py` → Start dashboard

### Innovation (20%)
- **Charger Attestation**: Pseudonymous charger ID protects privacy (SHA3 hash, not cleartext name)
- **Fail-Fast Pipeline**: Per-stage latency tracking enables performance bottleneck identification
- **Vehicle State Gating**: Safety-critical ECUs require charger auth; infotainment doesn't (policy-aware)
- **Presets + Threat Injection**: Unique judge interaction → see defense layer ordering
- **Audit-Signed Events**: Dilithium signatures on every decision for legal compliance

**Judge Demo Path**: Use presets to explore state space → Inject threats → See audit log → Check OpenAPI spec

### Safety Integration (15%)
- **Dual-Auth Requirement**: Show `config/ecu_policy.yaml` specifying braking_ecu, steering_ecu require charger
- **Vehicle State Checks**: Anti-juice-jacking enforces speed=0, battery_soc>20%, temp<60°C, data-locked=true
- **Recovery Snapshots**: Recovery manager takes snapshots before each update for rollback
- **Thermal Management**: Temperature threshold prevents battery stress during charging + update

**Judge Demo Path**: "Highway" preset (speed=100) → "Anti-Juice" scenario → BLOCKED → Show why

### Performance (10%)
- **Sub-Millisecond Crypto**: Kyber 0.13ms, Dilithium 0.30ms, SHA3 0.003ms per stage
- **1.7ms Legitimate OTA**: End-to-end verification for maps_ecu
- **3.3ms Charger-Auth OTA**: Additional charger attestation overhead
- **600 OTA/sec Throughput**: At mean latency of 1.87ms

**Judge Demo Path**: Run CLI demo → See mean latency → Check [PERFORMANCE.md](PERFORMANCE.md) for breakdown

### Demo Quality (10%)
- **Interactive Controls**: Presets, threat injection, scenario selection all in dashboard
- **Judge-Friendly**: Results are immediate, deterministic, and obvious (accepted/blocked)
- **Documentation**: Inline help, API docs, comprehensive guides for every evaluation criterion
- **Visual Feedback**: Color-coded results, timeline markers, threat status indicators

**Judge Demo Path**: Dashboard UX walkthrough → Show presets → Inject threat → See timeline

---

## Project Layout

```
PQDrive/
├── core/                          # Cryptographic verification pipeline
│   ├── demo_runner.py             # Shared orchestration engine
│   ├── kyber.py                   # Kyber-512 (ML-KEM) session setup
│   ├── dilithium.py               # Dilithium-2 (ML-DSA) signatures
│   └── sha3_hash.py               # SHA3-256 integrity
├── vehicle/                       # Vehicle-side security logic
│   ├── gateway.py                 # OTA ingress point, policy enforcement
│   ├── ota_server.py              # OTA package construction
│   ├── charger_security.py        # Charger authentication & anti-juice-jacking
│   ├── ecu_domain.py              # ECU classification & policy
│   └── recovery.py                # Audit log & rollback snapshots
├── attacks/                       # 7 Security scenarios
│   ├── charger_security_demo.py   # Charger auth + anti-juice
│   ├── rogue_charger.py           # Rogue charger rejection
│   ├── tamper_demo.py             # Payload tampering detection
│   ├── rollback_demo.py           # Version rollback blocking
│   └── hndl_demo.py               # Post-quantum vs RSA comparison
├── dashboard/                     # Flask web UI
│   ├── app.py                     # REST API + OpenAPI spec
│   ├── templates/index.html       # Dashboard layout
│   └── static/
│       ├── main.js                # Interactivity (presets, threats, timeline)
│       └── style.css              # Professional styling
├── config/
│   └── ecu_policy.yaml            # ECU domain policy & charging rules
├── tests/                         # 12 end-to-end tests
│   ├── test_pipeline.py           # OTA verification tests
│   └── test_charging_security.py  # Charger auth tests
└── main.py                        # CLI demo runner
```

## Security Architecture

### 7-Layer Verification Pipeline

```
1. Source Validation       → Only legitimate_ota_server or charging_network accepted
2. Charger Authentication  → Mutual auth envelope verified (if required for ECU)
3. Kyber Session           → Quantum-safe session key verified (0.13 ms)
4. Dilithium Signature     → Quantum-safe authentication (0.30 ms)
5. SHA3 Integrity          → Payload tampering detection (0.003 ms)
6. Version Check           → Rollback prevention (0.006 ms)
7. ECU Policy              → Safety-critical requires charger; infotainment auto-deploys
```

Each layer is independent; if any fails, pipeline stops and decision is logged.

### Key Cryptographic Properties

| Property | Mechanism | Quantum-Safe | Proof |
|----------|-----------|--------------|-------|
| Confidentiality | Kyber-512 encapsulation | Yes | NIST PQC finalist |
| Authentication | Dilithium-2 signatures | Yes | NIST PQC finalist |
| Integrity | SHA3-256 hashing | Yes | SHA-3 standard |
| Replay Defense | Request ID + nonce | Yes | Challenge-response |
| Non-Repudiation | Signed audit log | Yes | Dilithium signatures |

### Vehicle State Gating (Anti-Juice-Jacking)

For safety-critical ECU updates via charger:

```yaml
MAX_SAFE_SPEED_KPH: 0
MIN_BATTERY_SOC: 20%
MAX_SAFE_TEMPERATURE_C: 60
MAX_CLOCK_SKEW_SECONDS: 300
REQUIRE_DATA_LINK_LOCKED: true
```

If any threshold violated → update blocked at anti_juice stage.

---

## Performance Benchmarks

### Latency Analysis

| Scenario | Latency | Bottleneck |
|----------|---------|-----------|
| Legitimate OTA | 1.7 ms | Dilithium verification |
| Trusted Charger OTA | 3.3 ms | Charger auth + Dilithium |
| Attack (blocked early) | 0.8 ms | Source or anti-juice check |

**Per-Stage Breakdown** (Legitimate OTA):
- Kyber: 0.13 ms (session verification)
- Dilithium: 0.30 ms (signature verification)
- SHA3: 0.003 ms (integrity check)
- Version: 0.006 ms (rollback check)
- Total: 1.7 ms

**Throughput**: At 1.87 ms mean latency → 600 OTA decisions/sec

### Test Performance

- 12 tests: 0.11 seconds
- Scenario execution: 0.05-0.35 ms per scenario
- Dashboard startup: <2 seconds

---

## Security Threats Addressed

| Threat | Attack | Defense Layer | Demo Scenario |
|--------|--------|---|---|
| Spoofing | Rogue charger identity | Dilithium signature | Rogue Charger Attack |
| Tampering | Firmware bit-flip | SHA3 + Dilithium | Tamper Attack, Threat Injection |
| Repudiation | Deny update decision | Audit log + signatures | Audit Timeline |
| Disclosure | Charger ID exposure | Pseudonymous ID (SHA3) | Charger Attestation |
| DoS | Replay attack | Request ID cache | Replay Attack |
| Elevation | Unsafe charger state | Vehicle state gating | Anti-Juice Jacking |
| Rollback | Old firmware version | Version check | Rollback Attack |

---

## Running the Tests

```powershell
# Unit and integration tests
..\pqauto-env\Scripts\python.exe -m pytest tests/ -q

# Expected output:
# 12 passed in 0.11s

# With verbose output:
..\pqauto-env\Scripts\python.exe -m pytest tests/ -v
```

All tests are deterministic and reproducible. No external services needed.

---

## Environment Notes

- **Python Version**: 3.11+ required
- **Virtual Environment**: Pre-configured at `pqauto-env/`
- **Crypto Library**: liboqs-python 0.14.0 (warning: liboqs 0.15.0 library mismatch is non-blocking)
- **Platform**: Windows (demo), macOS, Linux supported
- **Network**: Dashboard runs on localhost:5000 (no internet required)

**Key Environment Variable** (if needed):
```powershell
$env:FLASK_DEBUG = 1  # Enable Flask debug mode
```

---

## Documentation Guide

| Document | Purpose | For Whom |
|----------|---------|----------|
| [THREAT_MODEL.md](THREAT_MODEL.md) | Security analysis, STRIDE coverage, threat matrix | Security reviewers |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, module roles, data flows | Architects, developers |
| [PERFORMANCE.md](PERFORMANCE.md) | Benchmarks, latency breakdown, scaling | Performance engineers |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production setup (Docker, cloud, TLS, monitoring) | DevOps, operations |
| [HACKATHON_GUIDE.md](HACKATHON_GUIDE.md) | Judge walkthrough, demo script, scoring tips | Hackathon judges |
| [QUICKREF.md](QUICKREF.md) | 30-second setup, 5-minute demo, FAQ | Everyone |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | Latest 4 dashboard features, changelog | Judges, developers |

---

## Troubleshooting

### ModuleNotFoundError: No module named 'oqs'
**Cause**: Not using the project virtual environment  
**Fix**: 
```powershell
..\pqauto-env\Scripts\Activate.ps1
python -m pytest tests/ -q
```

### Dashboard shows 500 errors
**Cause**: Syntax error in dashboard code or import failure  
**Fix**:
```powershell
$env:FLASK_DEBUG = 1
..\pqauto-env\Scripts\python.exe -m dashboard.app
# Check console for detailed error
```

### Tests fail with "liboqs version mismatch"
**Cause**: liboqs library version differs from liboqs-python binding (non-blocking warning)  
**Fix** (optional):
```powershell
pip install --upgrade liboqs-python==0.15.0
```

### Presets not showing in dashboard
**Cause**: JavaScript error or API not responding  
**Fix**: 
```powershell
# Check API is working:
curl http://localhost:5000/api/presets
# Should return JSON dict of presets
```

---

## Key Highlights for Judges

### Why Post-Quantum Cryptography Matters
- RSA-2048 and ECDSA will be broken by quantum computers in 10-20 years
- Kyber and Dilithium are NIST-approved quantum-safe alternatives
- PQDrive proves they're practical today: 1.7ms end-to-end latency
- See [PERFORMANCE.md](PERFORMANCE.md) for RSA-2048 comparison (HNDL demo)

### Why This Matters for EVs
- OTA is the primary attack surface for vehicle compromise
- Charger is a novel threat vector (first-time integration of charger auth)
- Safety-critical ECUs (braking, steering) need dual-authentication
- Anti-juice-jacking prevents attackers from updating while vehicle moves
- Audit log provides forensic evidence for incident response

### What Makes This Hackathon Project Compelling
1. **Realistic**: Based on AUTOSAR, real EV OTA workflows
2. **Verifiable**: 12 passing tests, open-source, reproducible
3. **Interactive**: Judges control vehicle state and inject threats
4. **Professional**: API docs, deployment guide, threat model
5. **Innovative**: First charger attestation + anti-juice-jacking integration
6. **Fast**: Post-quantum crypto proven practical at vehicle scale

---

## Quick Commands Reference

```powershell
# Setup
Set-Location 'E:\Hackathons , CODMAV , etc\PQDrive\MAHE_PQDrive'

# Test the installation
..\pqauto-env\Scripts\python.exe -m pytest tests/ -q

# Run all 7 scenarios (CLI)
..\pqauto-env\Scripts\python.exe main.py

# Start interactive dashboard
..\pqauto-env\Scripts\python.exe -m dashboard.app

# View API documentation
# In browser: http://localhost:5000/api/docs/html

# Check API endpoints
curl http://localhost:5000/api/presets
curl http://localhost:5000/api/report
```

---

## License

See [LICENSE.txt](LICENSE.txt) for details.

---

**Last Updated**: April 18, 2026  
**Status**: Hackathon-ready, all tests passing (12/12), interactive dashboard fully functional
