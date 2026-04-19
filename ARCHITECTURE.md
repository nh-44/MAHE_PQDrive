# PQDrive System Architecture

## High-Level Data Flow

```
┌─────────────────────┐
│   OTA Server        │
│ (Dilithium signing) │
└──────────┬──────────┘
           │
      ┌────▼────┐
      │ Package │ (Kyber-encapsulated, signed, versioned)
      └────┬────┘
           │
      ┌────▼───────────────────────────────┐
      │  Charger Network (Optional Path)   │
      │  ├─ Charger Auth Manager           │
      │  ├─ Attestation Envelope           │
      │  └─ Anti-Juice Verification        │
      └────┬───────────────────────────────┘
           │
      ┌────▼─────────────────────────────┐
      │  Vehicle Gateway (Entry Point)   │
      │  ├─ Source Validation             │
      │  ├─ Charger Auth Check (if req'd) │
      │  └─ Replay Detection              │
      └────┬─────────────────────────────┘
           │
      ┌────▼────────────────────────┐
      │ OTA Verification Pipeline   │
      ├─────────────────────────────┤
      │ 1. Kyber Session Verify     │
      │ 2. Dilithium Sig Verify     │
      │ 3. SHA3 Hash Verify         │
      │ 4. Version Check            │
      │ 5. ECU Policy Enforce       │
      └────┬────────────────────────┘
           │
      ┌────▼──────────────────────────┐
      │ Recovery & Audit Manager      │
      ├───────────────────────────────┤
      │ ✓ Pre-update snapshot         │
      │ ✓ Signed audit log            │
      │ ✓ Rollback capability         │
      │ ✓ ECU isolation on failure    │
      └───────────────────────────────┘
```

---

## Module Responsibilities

### Core Cryptography (`core/`)

#### `core/kyber.py`
- **Kyber512 / ML-KEM-512 KEM**
- Generate vehicle keypair on boot
- Encapsulate session key to vehicle public key
- Decapsulate and verify session key matches expected
- **Invoked by**: OTA server (to encapsulate) and gateway (to verify)

#### `core/dilithium.py`
- **Dilithium2 / ML-DSA-44 Signature**
- Server signs OTA payload with private key
- Gateway verifies signature with server public key
- Charger signs attestation envelope with its private key
- Gateway verifies charger attestation with charger public key
- **Invoked by**: OTA server and charger (to sign), gateway and recovery (to verify)

#### `core/sha3_hash.py`
- **SHA3-256 Integrity Hashing**
- Deterministic JSON serialization for payload + metadata
- Compute hex digest for OTA package
- Verify received digest matches payload bytes
- **Invoked by**: OTA server (to create) and pipeline (to verify)

#### `core/version_check.py`
- **Semantic Versioning with Rollback Prevention**
- Parse version strings to tuples (major, minor, patch)
- Enforce incoming > current (strict monotonicity)
- Reject downgrades and equal versions
- **Invoked by**: OTA verification pipeline (final gate)

#### `core/pipeline.py`
- **Fail-Fast Verification Pipeline**
- Execute checks in order: Kyber → Dilithium → Hash → Version
- Collect per-stage latency metrics
- Stop on first failure, return detailed trace
- **Invoked by**: Vehicle gateway after source/charger checks

#### `core/demo_runner.py`
- **Shared demo orchestration**
- Instantiate server, gateway, charger manager, recovery manager
- Run all scenarios (legitimate, charger OTA, juice-jacking, replay, rogue, rollback, tamper)
- Compute metrics (accept/block rate, mean latency, fastest stage)
- Return structured report for CLI and dashboard consumption

### Vehicle Side (`vehicle/`)

#### `vehicle/gateway.py` — OTA Entry Point
**Responsibilities**:
- Receive OTA request from network
- Replay detection (check request_id not seen before)
- Source validation (must be "legitimate_ota_server" or "charging_network")
- Charger auth check (if ECU requires authenticated charger)
  - Issue fresh nonce for this request
  - Verify charger attestation matches nonce + request_id + vehicle state
  - Reject if attestation is stale (> 300 sec old)
  - Reject if vehicle state is unsafe (moving, overheating, data-line open)
- Invoke pipeline for cryptographic verification
- Log request with timestamp and source for audit

**Critical Flow**:
```python
1. Check replay (request_id in _seen_request_ids) → reject if yes
2. Check source (must be in {"legitimate_ota_server", "charging_network"}) → reject if no
3. Check charger auth (if ECU policy requires it):
   - Verify charger envelope signature
   - Verify nonce matches challenge
   - Verify vehicle state digest
   - Verify attestation freshness
   - Reject on any failure
4. Run pipeline (Kyber, Dilithium, SHA3, Version)
5. Mark request_id as seen (replay prevention)
6. Return decision
```

#### `vehicle/ota_server.py` — Update Construction
**Responsibilities**:
- Generate OTA package with all required fields
- Encapsulate session key using vehicle's public key (Kyber)
- Sign payload with server private key (Dilithium)
- Hash payload for integrity check (SHA3)
- Include metadata: target_ecu, request_id, issued_at, expires_at, current_version, incoming_version

**Invoked by**: Demo runner to create test packages

#### `vehicle/charger_security.py` — Charger Attestation & Anti-Juice
**Responsibilities**:
- Register trusted chargers with pseudonymous identity
- Issue vehicle nonces for charger-to-vehicle mutual auth
- Build signed charger attestation envelopes
- Verify charger envelopes with multi-layer checks:
  1. Charger identity exists in registry
  2. Request ID matches (no mismatched requests)
  3. Request ID not replayed (seen before)
  4. Vehicle nonce matches challenge
  5. Vehicle state digest matches (no state tampering)
  6. Vehicle state is safe for OTA (speed, battery, temperature, data-line)
  7. Charger signature is valid
  8. Attestation not stale (< 300 sec old)

**Anti-Juice Checks** (`_is_safe_charging_state`):
- Vehicle speed = 0 (parked)
- Battery SOC ≥ 20% (not critically low)
- Data-line is locked (charging-only mode)
- Thermal state not hot/critical
- Battery temperature < 60°C

**Invoked by**: Gateway during charger-mediated OTA

#### `vehicle/ecu_domain.py` — Safety Policy
**Responsibilities**:
- Load ECU domain and policy from YAML config
- Classify ECU into domain: infotainment or safety_critical
- Answer policy queries:
  - `can_auto_deploy(ecu)` → infotainment auto-deploy true
  - `requires_dual_auth(ecu)` → safety-critical requires charger auth
  - `requires_authenticated_charger(ecu)` → safety-critical needs charger attestation

**Policy Enforcement**:
- Infotainment (maps, audio, Bluetooth): Direct OTA allowed, quick deploy
- Safety-critical (braking, steering, ADAS, powertrain): Charger auth required, dual authorization

**Invoked by**: Gateway to determine which checks to run

#### `vehicle/recovery.py` — Post-Update Recovery & Audit
**Responsibilities**:
- Snapshot pre-update state (firmware version, ECU health state)
- Log and sign all events for forensics
- Isolate compromised ECU (prevent spread via CAN)
- Rollback to last known-good state if available
- Maintain append-only signed audit log

**Key Functions**:
- `take_snapshot()` → Save state before update
- `isolate_ecu()` → Remove ECU from CAN bus
- `rollback()` → Restore from snapshot
- `log_event()` → Sign and append to audit log
- `get_audit_log()` → Return all events with signatures

**Invoked by**: Gateway on verification failure or anomaly detection

### Attack Simulations (`attacks/`)

#### `attacks/rogue_charger.py`
- Send OTA from fake charger source
- Expected outcome: Rejected at source validation (invalid source field)

#### `attacks/tamper_demo.py`
- Flip one byte in firmware payload
- Expected outcome: Rejected at Dilithium verification (signature mismatch)

#### `attacks/rollback_demo.py`
- Send update with lower version number
- Expected outcome: Rejected at version check (incoming < current)

#### `attacks/charger_security_demo.py`
- `simulate_authenticated_charger_update()` → Trusted charger with safe state → Accept
- `simulate_juice_jacking_attempt()` → Unsafe state (data-line unlocked) → Reject

#### `attacks/hndl_demo.py`
- Compare RSA-2048 vs Kyber512 ciphertext sizes
- Explain quantum harvest-now-decrypt-later vulnerability
- Show Kyber advantage in post-quantum readiness

### Dashboard (`dashboard/`)

#### `dashboard/app.py`
- Flask app with two routes:
  - `GET /` → Render HTML template
  - `GET /api/report` → Return JSON from `build_demo_report()`
- CORS-friendly JSON responses

#### `dashboard/templates/index.html`
- Hero section with project title and refresh button
- Threat model panel (entry points, attack paths, targets)
- Scenario results panel (before/after per attack)
- Performance metrics (accept/block rate, mean latency)
- Recommendations for production deployment

#### `dashboard/static/main.js`
- Fetch `/api/report` on page load
- Render threat model, scenarios, metrics
- Format pass/fail status with visual indicators

#### `dashboard/static/style.css`
- Dark theme with post-quantum color palette
- Responsive grid layout
- Card-based UI for scenarios and metrics

---

## Data Structures

### OTA Package (dict)
```python
{
    "ciphertext": bytes,              # Kyber-encapsulated session key
    "session_key": bytes,              # For gateway to verify Kyber decapsulation
    "signature": bytes,                # Dilithium signature of payload
    "payload": bytes,                  # Firmware binary
    "package_hash": str,               # SHA3-256 hex digest
    "incoming_version": str,           # Target version (e.g., "2.1.0")
    "current_version": str,            # Current version on vehicle
    "target_ecu": str,                 # ECU identifier (e.g., "braking_ecu")
    "request_id": str,                 # UUID for replay detection
    "issued_at": str,                  # ISO timestamp when created
    "expires_at": str,                 # ISO timestamp for freshness
    "source": str,                     # "legitimate_ota_server" or "charging_network"
}
```

### Pipeline Result (dict)
```python
{
    "kyber_ok": bool,
    "dilithium_ok": bool,
    "hash_ok": bool,
    "version_ok": bool,
    "all_passed": bool,
    "failed_at": str | None,           # Stage that failed
    "verification_trace": [            # Per-stage results
        {"stage": "kyber", "ok": bool, "duration_ms": float},
        ...
    ],
    "stage_durations_ms": {...},       # Latency per stage
    "veracity_score": float,           # 0.0 to 1.0 confidence
}
```

### Charger Auth Envelope (dict)
```python
{
    "charger_id": str,                 # Charger unique ID
    "pseudonymous_id": str,            # Privacy-preserving identifier for logs
    "charger_name": str,               # Human-readable name
    "request_id": str,                 # Links to OTA request
    "vehicle_nonce": str,              # Challenge from gateway
    "intent": str,                     # "ota" or other action
    "vehicle_state_digest": str,       # SHA3 of vehicle state
    "timestamp": str,                  # ISO when signed
    "signature": str,                  # Hex-encoded Dilithium sig
}
```

### Demo Report (dict)
```python
{
    "title": str,
    "threat_model": {
        "entry_points": [...],
        "attack_paths": [...],
        "target_systems": [...]
    },
    "policy": {
        "dual_auth_required_for": [...],
        "trusted_charger": str
    },
    "scenarios": [...],                # Array of scenario results
    "hndl": {...},                     # RSA vs Kyber comparison
    "recovery": [...],                 # Audit log events
    "metrics": {
        "scenario_count": int,
        "accepted_count": int,
        "blocked_count": int,
        "mean_latency_ms": float
    },
    "recommendations": [...]
}
```

---

## Key Design Decisions

### 1. Fail-Fast Pipeline
**Why**: Stop verification at first failure to minimize exposure window and latency
**Trade-off**: Less granular error details (but still logged per stage)

### 2. Pseudonymous Charger IDs
**Why**: Privacy in audit logs; production should use X.509 certs
**Trade-off**: Weaker identity assurance in demo (acceptable for hackathon scope)

### 3. Request ID + Nonce Replay Prevention
**Why**: Two-layer defense; request ID prevents same package re-use, nonce prevents charger attestation re-use
**Trade-off**: Requires in-memory cache (production needs durable store)

### 4. Vehicle State Gating
**Why**: Prevent OTA during unsafe conditions (moving, overheating, battery critical)
**Trade-off**: Updates blocked during degraded battery; users must wait for safe state

### 5. Charger Policy Enforcement at Gateway
**Why**: Centralized, easy to audit decision logic
**Trade-off**: Charger learns which ECUs are safety-critical; mitigated by pseudonymous ID

---

## Performance Characteristics

### Crypto Operations (per stage, ms)
- Kyber encapsulation: ~0.13 ms (network-driven, not computation-heavy)
- Dilithium signature verification: ~0.29 ms (dominant cost)
- SHA3-256 hashing: ~0.003 ms (negligible)
- Version check: ~0.006 ms (negligible)

### End-to-End OTA Latency
- Legitimate OTA: ~1.7 ms
- Trusted Charger OTA: ~3.3 ms (includes charger auth verification)
- Blocked (fast-path): ~0.004 ms (source validation fail)

### Throughput
- ~600 OTA decisions/second (single-threaded)
- ~150 OTA decisions/second with charger auth overhead

---

## Deployment Target

### Supported Platforms
- Linux (tested: Ubuntu 22.04, Alpine 3.16)
- Windows (tested: Windows 11 with Python 3.11)
- macOS (untested but likely compatible)

### Container
- Docker image with Python 3.11-slim base
- All dependencies in requirements.txt
- Expose port 5000 for dashboard

### Runtime Requirements
- Python 3.9+
- liboqs (post-quantum crypto bindings)
- Flask + Flask-SocketIO (dashboard)
- ZeroMQ (CAN simulation)

*See DEPLOYMENT.md for detailed setup instructions.*

---

*Document Version: 1.0 | Last Updated: April 18, 2026*
