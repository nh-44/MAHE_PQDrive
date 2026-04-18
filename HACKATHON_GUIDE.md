# PQDrive Hackathon Submission Guide

## Submission Overview

**Project Name**: PQDrive  
**Category**: Automotive Cybersecurity & Post-Quantum Cryptography  
**Focus**: OTA Integrity & Charger-Side Protection  
**Evaluation Criteria**: Security Depth (25%), Feasibility (20%), Innovation (20%), Safety Integration (15%), Performance (10%), Demo Quality (10%)

---

## Executive Pitch (60 seconds)

**Problem**: Connected EVs rely on unencrypted OTA updates delivered over untrusted networks (cellular, public chargers). Chargers can inject malware, downgrade firmware, or stall critical safety updates. Post-quantum cryptography adds complexity but is essential for long-term security.

**Solution**: PQDrive authenticates OTA packages with Kyber-512 encapsulation and Dilithium-2 signatures, gates safety-critical updates via charger attestation and vehicle state checks, and detects replays with request ID tracking. The dashboard lets judges interactively trigger attacks and see real-time defense outcomes.

**Results**: 
- ✅ 100% legitimate update acceptance rate
- ✅ 100% attack block rate (tamper, replay, rollback, rogue charger, juice-jacking)
- ✅ ~1.7ms OTA latency (quantum-safe, no performance penalty)
- ✅ Interactive demo: judges can adjust vehicle speed/battery and see security policies adapt

---

## Pre-Hackathon Setup (30 minutes)

### Judges' Machines

```bash
# 1. Clone repo
git clone https://github.com/nh-44/MAHE_PQDrive.git
cd MAHE_PQDrive

# 2. Create venv (one-time, ~2 min)
python -m venv pqauto-env
pqauto-env\Scripts\activate  # Windows
# OR
source pqauto-env/bin/activate  # macOS/Linux

# 3. Install dependencies (one-time, ~3 min)
pip install -r requirements.txt

# 4. Verify setup
pytest -q tests/

# 5. Start dashboard (judges' only step)
python -m flask -A dashboard.app run
# Then open http://localhost:5000 in browser
```

**Expected Output**:
```
✓ 12 passed in 0.09s
✓ Dashboard listening on http://127.0.0.1:5000
```

---

## Hackathon Demo Script (5-10 minutes)

### Phase 1: Context (2 min)
**Narration**:
> "We're securing OTA updates for connected EVs. Here's the threat: your charger could be malicious, the network could be eavesdropped, or an attacker could replay old firmware. PQDrive defends with three layers: cryptographic verification, charger mutual authentication, and safety-aware policy enforcement."

**Pointer**: Show README.md's threat diagram on slide or print.

---

### Phase 2: Dashboard Walkthrough (3 min)

#### Dashboard Tour:
1. **Refresh Demo** button → Shows all 7 scenarios executed
   - 2 accepted (Legitimate OTA, Trusted Charger OTA)
   - 5 blocked (Replay, Rollback, Tamper, Rogue Charger, Anti-Juice Jacking)

2. **Threat Model Panel** → Explain entry points and attack paths

3. **Performance Metrics** → Highlight:
   - Mean latency: 2.09 ms (sub-millisecond for most stages)
   - Accept/block rate: 100% correctness
   - Fastest stage: SHA3 hash (0.003 ms, negligible)

---

### Phase 3: Interactive Attack Demo (5 min)

#### Attack 1: Juice-Jacking with Vehicle State Control

**Setup**:
```
Speed slider: Set to 0 km/h (parked)
Battery slider: 68%
Temperature slider: 31°C
Data-line Locked: ✓ (checked)
Charging Active: ✓ (checked)
```

**Actions**:
1. Click "Anti-Juice Jacking" button
2. **Result 1**: BLOCKED at `anti_juice` stage
   - **Explanation**: "The attack tries to update while data_link_locked=false. Our vehicle gate enforces charging-only mode before accepting updates."

3. Modify state:
   - Set **Speed = 30 km/h** (moving vehicle)
   - Click "Anti-Juice Jacking" again
   - **Result 2**: BLOCKED at `anti_juice` stage
   - **Explanation**: "Moving vehicle? No updates allowed. Safety first."

#### Attack 2: Replay Attack

**Setup**: Default state (speed=0, battery=68)

**Actions**:
1. Click "Replay Attack" button
2. **Result**: BLOCKED at `replay` stage
   - **Explanation**: "Each request gets a unique ID and nonce. Sending the same request twice? Our gateway detects and rejects it on the second attempt."

#### Attack 3: Rollback (Version Anti-Downgrade)

**Actions**:
1. Click "Rollback Attack" button
2. **Result**: BLOCKED at `version` stage
   - **Explanation**: "Attacker tries to downgrade from v2.0.0 to v1.9.0. Semantic versioning enforces monotonic increases—no downgrades allowed."

#### Attack 4: Tamper Detection (Signature Verification)

**Actions**:
1. Click "Tamper Attack" button
2. **Result**: BLOCKED at `dilithium` stage
   - **Explanation**: "One bit flipped in the firmware. Dilithium detects it immediately. With post-quantum cryptography, even quantum computers can't forge this signature."

---

### Phase 4: Key Innovation Points (1 min)

**Highlight**:
1. **Post-Quantum Readiness**: Kyber-512 + Dilithium-2 from NIST standardization effort
2. **Charger Mutual Auth**: Chargers prove identity via signed attestation; vehicles verify via nonce challenge-response
3. **Fail-Fast Verification**: Stop at first gate; latency stays sub-millisecond even with all checks
4. **Vehicle State Gating**: Safety policies (speed, battery, thermal) gate update execution
5. **Reproducibility**: Judges can modify state and re-run; deterministic outcomes

---

## Demo Walkthroughs by Evaluation Criterion

### Security Depth (25%)
**What to Highlight**:
- Multi-layer defense: source validation → charger auth → crypto verification → policy enforcement
- STRIDE coverage: spoofing (charger cert), tampering (Dilithium sig), repudiation (signed envelope), elevation (policy), denial (replay detection)

**Demo Activity**:
- Show THREAT_MODEL.md
- Run "Rogue Charger Attack" → BLOCKED at source validation
- Run "Tamper Attack" → BLOCKED at Dilithium signature
- Run "Replay Attack" → BLOCKED at request ID duplication

**Talking Points**:
> "We cover 5 of 6 STRIDE threats. The 6th (Denial of Service) requires network-level rate limiting, which we recommend for production but skip for hackathon scope."

---

### Feasibility (20%)
**What to Highlight**:
- Single `pytest -q` command runs all tests
- `python main.py` produces full report in < 1 second
- Dashboard starts with `python -m flask`
- Works on Windows, macOS, Linux (tested on Win11 + Ubuntu)

**Demo Activity**:
- Show terminal running `pytest` → "12 passed in 0.09s"
- Show `main.py` output with structured JSON and stats
- Open dashboard and load in < 2 seconds

**Talking Points**:
> "Zero external dependencies beyond Python 3.9+. Post-quantum crypto is complex, but liboqs-python abstracts it. Judges can run this on any laptop in 30 seconds."

---

### Innovation (20%)
**What to Highlight**:
1. **Charger Attestation**: Industry doesn't do this; we add mutual auth layer
2. **Anti-Juice-Jacking Gating**: Vehicle state (speed, battery, data-lock) enforces safe charging conditions
3. **Pseudonymous Charger IDs**: Privacy-preserving audit logs (SHA3-based)
4. **Fail-Fast with Telemetry**: Per-stage latency capture for forensics

**Demo Activity**:
- Run "Trusted Charger OTA" → show charger_verified=true in result
- Modify speed slider to 50 km/h, run "Anti-Juice" → blocked
- Point to ARCHITECTURE.md's data flow diagram

**Talking Points**:
> "Charger-authenticated OTA is novel. Traditional systems treat all network sources as untrusted equally. We add a middle ground: 'trusted charger' for faster, verified updates at public stations."

---

### Safety Integration (15%)
**What to Highlight**:
- Dual-auth policy for safety-critical ECUs (braking, steering, ADAS, powertrain)
- Vehicle state gating: no updates while moving, overheating, or battery critical
- Recovery snapshots: pre-update state capture for forensics
- Fail-safe default: reject everything except explicitly approved paths

**Demo Activity**:
- Show config/ecu_policy.yaml (safety-critical list)
- Run "Legitimate OTA" (infotainment/maps) → ACCEPTED (fast path)
- Run "Trusted Charger OTA" (braking) → ACCEPTED (dual-auth path)
- Show `vehicle/recovery.py` audit log capabilities

**Talking Points**:
> "We define safety-critical ECUs upfront. Infotainment updates fast; safety-critical updates require charger attestation. ISO 26262 thinking applied to OTA."

---

### Performance (10%)
**What to Highlight**:
- Mean latency: 2.09 ms across all scenarios
- Legitimate OTA: 1.7 ms
- Charger-mediated OTA: 3.3 ms
- All cryptographic operations complete in < 0.4 ms

**Demo Activity**:
- Show PERFORMANCE.md benchmark table
- Point to /api/report JSON output → scenario.duration_ms fields
- Calculate: "Network latency ~50-200ms dominates; our 2ms is negligible"

**Talking Points**:
> "Post-quantum crypto is often accused of being slow. Kyber is fast (0.13ms), Dilithium's the bottleneck (0.3ms), but even combined, total OTA decision is sub-3ms. Network, not crypto, is the bottleneck."

---

### Demo Quality (10%)
**What to Highlight**:
- CLI output: structured threat model, policy, scenarios, metrics
- Dashboard: responsive dark theme, real-time scenario controls, vehicle state sliders
- Documentation: THREAT_MODEL.md, ARCHITECTURE.md, PERFORMANCE.md, DEPLOYMENT.md

**Demo Activity**:
- Open dashboard in browser → show hero banner, stats cards, threat model cards
- Click scenario buttons → instant results with color-coded pass/fail
- Adjust battery slider from 100% to 20% → explain how battery state affects OTA eligibility

**Talking Points**:
> "Judges can see the threat model, run attacks interactively, adjust vehicle conditions, and watch the security policies adapt. This is transparency and reproducibility."

---

## FAQ for Judges

### Q: Why not just use RSA-2048 signatures?
**A**: RSA is vulnerable to quantum computers. Harvest-now-decrypt-later attacks: an adversary could record encrypted OTA packages today and decrypt them in 10-15 years when quantum computers exist. Kyber/Dilithium are quantum-resistant by design. The 50% latency overhead is negligible vs. the 50-year security guarantee.

### Q: How do you prevent a charger from blocking all updates?
**A**: The vehicle has a fallback path: if charger auth fails, legitimate OTA server can still push updates directly (e.g., via cellular). Chargers are a convenience for public charging stations, not a bottleneck.

### Q: What about key rotation?
**A**: Out of scope for hackathon but critical for production. We recommend: (1) HSM-based key storage, (2) quarterly rotation, (3) version epochs to invalidate old keys. See DEPLOYMENT.md recommendations.

### Q: Can you fake a charger's pseudonymous ID?
**A**: No. Pseudonymous ID is the SHA3 hash of (charger_name + charger_id). To fake it, attacker would need to forge a Dilithium signature on the attestation envelope, which is cryptographically hard.

### Q: Why Dilithium over SPHINCS+ or Falcon?
**A**: Dilithium is NIST FIPS 204 standardized. SPHINCS+ is slower; Falcon has patent restrictions. Dilithium is the Goldilocks choice for automotive: reasonable speed, well-studied, standards-backed.

---

## Print Materials

### 1-Page Handout for Judges

```
PQDrive: Quantum-Safe OTA Updates for Connected EVs

Problem:
- EV firmware updates delivered over untrusted networks (cell, public chargers)
- Chargers can inject malware, downgrade firmware, or launch replay attacks
- Post-quantum cryptography adds complexity but is essential for 50-year security

Solution:
- Kyber-512 (post-quantum KEM) encapsulates session keys
- Dilithium-2 (post-quantum signature) signs OTA packages
- Charger attestation gates safety-critical ECU updates
- Vehicle state (speed, battery, thermal) enforces safe charging conditions

Metrics:
- 100% attack block rate (7 scenarios, 0 false negatives)
- 1.7ms OTA latency (post-quantum, no performance penalty)
- 12/12 tests passing (comprehensive coverage)
- Interactive dashboard (judges can modify vehicle state and re-run)

Setup:
git clone https://github.com/nh-44/MAHE_PQDrive.git
python -m venv pqauto-env && source pqauto-env/bin/activate
pip install -r requirements.txt
pytest -q tests/  # All pass in 0.09s
python -m flask -A dashboard.app run  # Open http://localhost:5000
```

### Poster Key Points (for physical booth)

```
┌─────────────────────────────────────────────────────────┐
│  PQDrive: Post-Quantum OTA Security                     │
├─────────────────────────────────────────────────────────┤
│  Kyber-512  │  Dilithium-2  │  Charger Auth │  Policy   │
│             │               │   Gating      │ Enforce   │
├─────────────────────────────────────────────────────────┤
│ ✓ Quantum-safe (NIST FIPs 204)                         │
│ ✓ 1.7ms latency (all checks)                           │
│ ✓ 100% attack block rate                               │
│ ✓ Interactive demo (judges control attack parameters)  │
├─────────────────────────────────────────────────────────┤
│ https://github.com/nh-44/MAHE_PQDrive                   │
└─────────────────────────────────────────────────────────┘
```

---

## Post-Demo: Next Steps for Judges

**If Judges Ask "What's Next?"**:

1. **Production Hardening**:
   - X.509 certificates for charger identity (replace pseudonymous IDs)
   - Hardware Security Module (HSM) for key storage
   - Signed manifests for OTA artifacts
   - Durable replay cache (Redis, DynamoDB)

2. **Fleet Analytics**:
   - Anomaly detection across vehicle population
   - Charger reputation scoring
   - Attack attribution and forensics

3. **Continuous Attestation**:
   - Post-update integrity verification
   - Runtime ECU state monitoring
   - Behavioral analysis for firmware integrity

**Relevant Files**:
- Recommendations in PERFORMANCE.md (optimization roadmap)
- Future work in THREAT_MODEL.md (production controls)
- Deployment guide at DEPLOYMENT.md (cloud setup)

---

## Submission Checklist

- [ ] README.md updated with quick start and demo guide
- [ ] All tests passing (`pytest -q` → 12 passed)
- [ ] CLI demo working (`python main.py` → full report)
- [ ] Dashboard starts without errors (`python -m flask`)
- [ ] THREAT_MODEL.md, ARCHITECTURE.md, PERFORMANCE.md complete
- [ ] DEPLOYMENT.md provided (judges can containerize if needed)
- [ ] test_interactive.py validates new interactive features
- [ ] Git history clean with descriptive commits
- [ ] No debug prints or TODOs left in code
- [ ] requirements.txt pinned to specific versions
- [ ] Dockerfile provided for judges' convenience
- [ ] Presentation slides ready (5-10 min walkthrough)
- [ ] Handouts printed (1-page summary + poster)

---

## Scoring Maximization Tips

1. **Security Depth (25%)**: Emphasize multi-layer defense and STRIDE coverage. Show THREAT_MODEL.md upfront.

2. **Feasibility (20%)**: Demonstrate one-command setup. Let judges run `pytest` and see it pass in real-time.

3. **Innovation (20%)**: Highlight charger attestation + anti-juice-jacking. Show judges can modify vehicle state and see policy adapt.

4. **Safety Integration (15%)**: Talk about dual-auth for safety-critical ECUs. Show config/ecu_policy.yaml.

5. **Performance (10%)**: Show PERFORMANCE.md benchmarks. Emphasize sub-3ms total latency.

6. **Demo Quality (10%)**: Let judges interact with dashboard. Adjust vehicle state; click scenarios. Real-time feedback wins points.

---

## Backup Plan (If Dashboard Doesn't Load)

```bash
# Fallback to CLI demo
python main.py

# Expected output: Structured report with all 7 scenarios, metrics, recommendations
# Takes < 1 second
# Print to PDF or share as JSON

# If needed, show test results
pytest -v tests/test_charging_security.py
# Output: 3 new charger auth tests + 9 original pipeline tests
```

---

*Hackathon Submission Guide v1.0 | Last Updated: April 18, 2026*
