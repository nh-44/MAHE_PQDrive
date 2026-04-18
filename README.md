# PQDrive

PQDrive is a hackathon demo for post-quantum OTA trust, charger-mediated vehicle update protection, and safety-aware recovery for connected EVs.

## What it demonstrates

- Post-quantum OTA trust using Kyber/ML-KEM and Dilithium/ML-DSA primitives.
- Integrity checks with SHA3 and rollback protection.
- Charger-side mutual authentication for vehicle updates delivered over the charging network.
- Anti-juice-jacking gating that blocks unsafe charging states before OTA execution.
- Recovery and audit evidence for failed or suspicious update attempts.
- A live dashboard showing scenario outcomes, metrics, and threat model context.

## Project layout

- `core/`: cryptographic verification pipeline and shared demo runner.
- `vehicle/`: gateway, OTA server, charger attestation, ECU policy, and recovery logic.
- `attacks/`: rogue charger, tamper, rollback, HNDL, and charger-security demo scenarios.
- `dashboard/`: Flask UI for live demo reporting.
- `tests/`: end-to-end and charger-security tests.

## How to run

Use the project virtual environment because the global Python environment does not have the required `oqs` bindings.

```powershell
Set-Location 'E:\Hackathons , CODMAV , etc\PQDrive\MAHE_PQDrive'
..\pqauto-env\Scripts\python.exe -m pytest -q
..\pqauto-env\Scripts\python.exe main.py
..\pqauto-env\Scripts\python.exe -m dashboard.app
```

Open the dashboard at `http://127.0.0.1:5000` after starting it.

## Demo story

1. Show a legitimate OTA package passing all checks.
2. Show a trusted charger forwarding an update to a safety-critical ECU.
3. Show anti-juice-jacking rejection when the charger session is unsafe.
4. Show rollback and tamper attacks failing at the right stage.
5. Show the HNDL comparison explaining why post-quantum key exchange matters.

## Security notes

- Safety-critical ECUs require stronger authorization than infotainment ECUs.
- Charger authentication uses pseudonymous charger identity to avoid exposing the physical charger name in logs.
- Replay protection is enforced through request IDs, pending challenges, and attestation freshness.

## Known environment note

The installed Python environment currently reports a version mismatch warning between liboqs and liboqs-python. The demo still runs, but aligning those versions is recommended before a public deployment.

## 📚 Comprehensive Documentation

For detailed information, see:
- **[THREAT_MODEL.md](THREAT_MODEL.md)** — Security analysis, STRIDE coverage, attack scenarios
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System design, module roles, data flows, cryptographic details
- **[PERFORMANCE.md](PERFORMANCE.md)** — Benchmarks, latency breakdown, scaling recommendations
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Production deployment (Docker, cloud, TLS, monitoring)
- **[HACKATHON_GUIDE.md](HACKATHON_GUIDE.md)** — Judging walkthrough, demo script, FAQ, scoring tips

## 🎮 Interactive Dashboard

The dashboard provides live scenario controls:

```bash
python -m flask -A dashboard.app run
# Open http://localhost:5000
```

**Features**:
- Adjust vehicle state (speed, battery, temperature, data-lock) with sliders
- Select and run any of 7 scenarios interactively
- See real-time results (accepted/blocked, latency, failure reason)
- Explore how vehicle state affects security policy decisions

**Example Experiments**:
- "Can I charge while moving?" → Set speed=50, run Anti-Juice Jacking → BLOCKED
- "Does my battery protect me?" → Set battery=5%, run scenarios → Observe policy differences
- "What stops replay attacks?" → Run Replay Attack twice → Blocked both times (in cache)

## 📊 Performance Highlights

| Metric | Value |
|--------|-------|
| Legitimate OTA Latency | 1.7 ms |
| Charger-Auth OTA Latency | 3.3 ms |
| Attack Block Rate | 100% (5/5) |
| Tests Passing | 12/12 |
| Mean Throughput | 600 OTA decisions/sec |

**Cryptographic Breakdown**:
- Kyber-512 verification: 0.13 ms
- Dilithium-2 verification: 0.30 ms
- SHA3-256 hashing: 0.003 ms
- Version check: 0.006 ms

## 🛡️ Security Layers

1. **Source Validation** → Block invalid sources
2. **Charger Authentication** (optional) → Verify charger identity & vehicle state
3. **Kyber Session Verification** → Quantum-safe session key
4. **Dilithium Signature Verification** → Quantum-safe authentication
5. **SHA3 Integrity Check** → Detect payload tampering
6. **Version Check** → Prevent rollback attacks
7. **ECU Policy Enforcement** → Dual-auth for safety-critical ECUs

## 🎯 Hackathon Evaluation Coverage

| Criterion | Coverage |
|-----------|----------|
| Security Depth (25%) | Multi-layer defense, STRIDE analysis, charger auth, anti-juice-jacking |
| Feasibility (20%) | One-command setup, 12 tests in 0.09s, works on Windows/macOS/Linux |
| Innovation (20%) | Charger attestation, pseudonymous IDs, fail-fast telemetry, policy-aware gating |
| Safety Integration (15%) | Dual-auth for safety-critical, vehicle state gating, recovery snapshots |
| Performance (10%) | 1.7ms OTA latency, 600 OTA/sec, sub-millisecond per crypto stage |
| Demo Quality (10%) | Interactive dashboard, judges control vehicle state, deterministic outcomes |

## 🆘 Quick Troubleshooting

**"ModuleNotFoundError: No module named 'oqs'"**
→ Virtual environment not activated. Run: `pqauto-env\Scripts\activate`

**"liboqs version mismatch warning"**
→ Non-blocking. To fix: `pip install --upgrade liboqs-python==0.15.0`

**"Dashboard returns 500 errors"**
→ Enable debug: `export FLASK_DEBUG=1` (on macOS/Linux) or set in PowerShell

For more detailed troubleshooting, see [DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting).
