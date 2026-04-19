# PQDrive Threat Model

## Executive Summary

PQDrive protects automotive OTA updates delivered over the charging network using post-quantum cryptography and safety-aware policy enforcement. This document details the threat model, attack scenarios, and mitigations for a connected EV platform.

---

## 1. System Scope

### Stakeholders
- **OTA Server**: Centralized update authority (trusted, managed by OEM)
- **Vehicle Gateway**: Entry point for OTA packages (in-vehicle, untrusted network boundary)
- **ECU Domains**: Safety-critical (braking, steering, ADAS, powertrain) and infotainment (maps, audio, Bluetooth)
- **Charger Network**: Third-party charging infrastructure (low-trust delivery channel)
- **Recovery Manager**: Post-update validation and forensic auditing

### Assets
- **Firmware Packages**: Code and configuration for all ECUs
- **Cryptographic Keys**: Vehicle and charger identity keys, OTA server signing key
- **Version Metadata**: Current firmware versions, rollback prevention state
- **Vehicle State**: Battery, thermal, safety signal health for gating update execution
- **Audit Trail**: Signed evidence of all update decisions

---

## 2. Attack Surface

### Entry Point 1: OTA Request Ingress at Gateway
**Data Flow**: Network → Gateway receive_update_request() → Pipeline validation

**Threat Agents**:
- Rogue charger: Malicious charging station posing as legitimate
- MITM attacker: Intercepting network traffic
- Replay attacker: Re-sending captured valid packages

**Attack Vectors**:
1. **Rogue Source Spoofing**: Send OTA package with fake "source" field
2. **Payload Tampering**: Modify firmware bytes in-transit
3. **Rollback Attack**: Send downgrade package with lower version
4. **Replay Attack**: Re-send old valid package to apply stale firmware

### Entry Point 2: Charger-Mediated Updates (Bonus Path)
**Data Flow**: Charging network → Charger auth envelope → Gateway policy check

**Threat Agents**:
- Rogue charging station: Compromised or fake charger
- Data-line exploiter: Attacker with physical access to charging port
- Juice-jacking operator: Charger injecting malware or extracting data

**Attack Vectors**:
1. **Unauthorized Charger**: Charger not in trusted registry
2. **Unsafe Charging State**: Update during hot battery, moving vehicle, or data-line unlocked
3. **Charger Attestation Replay**: Reuse of old charger signature for new requests
4. **Policy Bypass**: Attempt to update safety-critical ECU without dual authorization

### Entry Point 3: CAN Bus Simulation (Auxiliary)
**Data Flow**: Inter-ECU messaging via ZeroMQ

**Threat Agents**:
- Network eavesdropper: Monitor vehicle internal comms

**Attack Vectors**:
1. **Message Eavesdropping**: Capture unencrypted CAN payloads
2. **ECU Spoofing**: Fake ECU responses to health queries

---

## 3. Target Systems & Critical Operations

### Gateway Decision Logic (Core Target)
- **Accept legitimate OTA**: Allow valid updates from authorized source
- **Block rogue source**: Reject updates claiming fake charger/server
- **Block tampered payload**: Detect payload mutation via signature/hash
- **Block rollback**: Prevent downgrade to older firmware versions
- **Block replay**: Reject re-use of old request IDs and nonces
- **Block unsafe charger state**: Reject updates during hot/moving conditions

### Recovery & Isolation
- **Snapshot**: Capture pre-update state for rollback
- **Isolation**: Prevent compromised ECU from spreading via CAN
- **Audit**: Log all decisions with cryptographic evidence

---

## 4. Threat Model Matrix

| Threat | Severity | Likelihood | Impact | Mitigation |
|--------|----------|------------|--------|------------|
| Rogue Charger OTA | High | Medium | ECU compromise, vehicle safety | Source field validation + charger attestation |
| Payload Tamper | High | Medium | Code execution via corrupted firmware | Dilithium signature + SHA3 hash verification |
| Rollback Attack | High | Low | Revert to known-vulnerable firmware | Monotonic version checks with enforcement |
| Replay Attack | High | Medium | Apply stale firmware with old bugs | Request ID + nonce + freshness checks |
| Juice-Jacking | High | Medium | Vehicle data exfiltration | Data-line lock + charger mutual auth |
| Key Compromise | Critical | Low | All OTA security broken | Key rotation + HSM/TPM in production |
| Quantum Decryption | Medium | Low | Future harvest-now-decrypt-later | Post-quantum Kyber/Dilithium |

---

## 5. Security Properties & Guarantees

### Cryptographic Guarantees
- **Key Encapsulation**: Kyber512 ensures session key confidentiality against quantum adversaries
- **Authentication**: Dilithium2 ensures OTA package authenticity and non-repudiation
- **Integrity**: SHA3-256 ensures payload was not modified in-transit
- **Rollback Prevention**: Semantic version checks prevent downgrade to older versions

### Operational Guarantees
- **Fail-Safe Default**: Reject by default; accept only after all checks pass
- **Fail-Fast Verification**: Stop at first check failure, no partial acceptance
- **Charger Mutual Auth**: Chargers must prove identity via signed attestation
- **Replay Resistance**: Each request ID + nonce pair is valid only once
- **Freshness Enforcement**: Attestation timestamps rejected if > 300 seconds old
- **Safety Gating**: Safety-critical ECUs require dual authorization + safe vehicle state

---

## 6. Deployment Security Controls

### In Production (Beyond Scope, Recommended)
1. **Certificate-Based Charger Attestation**: Replace pseudonymous IDs with X.509 certs
2. **Hardware Security Module (HSM)**: Secure key storage and signing
3. **Secure Enclave**: Run gateway logic in trusted execution environment (TEE)
4. **Network Security**: Mutual TLS between OTA server and gateway
5. **Forensic Logging**: Durable, signed audit log with event chaining
6. **Recovery Playbook**: Automated incident response for detected attacks

### In This Demo
- ✅ Post-quantum crypto (Kyber, Dilithium)
- ✅ Payload integrity (SHA3)
- ✅ Replay protection (request ID, nonce, freshness)
- ✅ Charger attestation (pseudonymous ID, signed envelope)
- ✅ Anti-juice-jacking (vehicle state gating)
- ✅ Recovery snapshots and audit logging
- ⚠️ TPM/HSM not available in simulation
- ⚠️ TLS only used in production deployment

---

## 7. Evaluation Against STRIDE

| Threat | Category | Scenario | Mitigation | Status |
|--------|----------|----------|-----------|--------|
| Spoofing | S | Rogue charger claims to be trusted | Source validation + attestation | ✅ Mitigated |
| Tampering | T | Payload bytes flipped in-transit | Dilithium sig + SHA3 hash | ✅ Mitigated |
| Repudiation | R | Charger denies sending update | Signed charger envelope | ✅ Mitigated |
| Information Disclosure | I | Charger identity exposed in logs | Pseudonymous ID in audit log | ⚠️ Reduced (demo) |
| Denial of Service | D | Flood gateway with invalid packages | Rate limiting (future enhancement) | ⚠️ Out of scope |
| Elevation of Privilege | E | Infotainment ECU alters safety-critical | ECU domain + policy enforcement | ✅ Mitigated |

---

## 8. Known Limitations & Future Work

### Current Scope
- Threat model covers OTA delivery and charger-side gating
- Single vehicle instance (no fleet coordination)
- Simulated CAN bus (no real-time constraints)
- Demo uses pseudonymous charger IDs (production needs certs)

### Future Enhancements
1. **Distributed Trust**: Multi-OEM update coordination and delegation
2. **Fleet Analytics**: Anomaly detection across vehicle population
3. **Continuous Attestation**: Runtime integrity verification post-update
4. **Secure Boot**: Measured boot chain from hardware to ECU firmware
5. **Supply Chain Security**: Signed manifest for build artifacts

---

## 9. Compliance & Standards References

- **NIST Cybersecurity Framework**: Risk management, threat analysis
- **AUTOSAR Security**: Automotive-grade cryptographic primitives
- **OWASP Top 10**: Common attack patterns addressed
- **ETSI QSC**: Post-quantum cryptography readiness
- **ISO 26262**: Functional safety (applies to recovery mechanisms)

---

## 10. Contact & Escalation

For security issues in production deployments, follow the responsible disclosure process:
1. Do NOT disclose publicly
2. Contact: security@pqdrive-oem.example.com
3. Provide PoC, impact assessment, and timeline
4. Participate in coordinated disclosure window

---

*Document Version: 1.0 | Last Updated: April 18, 2026 | Classification: Hackathon Public*
