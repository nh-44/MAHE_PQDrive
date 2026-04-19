# PQDrive: Post-Quantum OTA Security Demo

PQDrive is a connected-vehicle OTA security demo that shows how a post-quantum verification pipeline blocks unsafe and malicious firmware updates.

## Latest Update (Current)

This version includes the recent implementation changes:

- HNDL resistance flow integrated as a first-class scenario (Kyber vs classical comparison)
- Final-stage payload tamper detection aligned with trusted BUILD hash verification
- Dashboard UI simplified by removing attack scenario cards, security features panel, and audit log section from the right panel
- Real-time metrics fixed to update immediately after every run path (accepted, blocked, interrupted/error)
- New metric added: Latest Request Total Time (start to completion/interruption)
- Right-side dashboard panel width increased and text sizes slightly increased for readability

## Core Security Pipeline

The OTA flow validates firmware in fail-fast order:

1. Delivery gate (vehicle state + source + channel)
2. Freshness window
3. Kyber KEM session verification
4. Dilithium signature verification
5. SHA3-256 integrity verification
6. Anti-rollback version validation
7. ECU target allowlist validation

Any failed stage blocks installation.

## Project Structure

- core/: classification, verification pipeline, and demo runner
- attacks/: scenario implementations including HNDL demo
- dashboard/: Flask dashboard app and UI templates
- tests/: pipeline, payload classifier, and integration checks
- vehicle/: gateway and OTA orchestration components

## Quick Start

```powershell
# 1) Open repo
Set-Location 'E:\Hackathons , CODMAV , etc\PQDrive\MAHE_PQDrive'

# 2) Run tests
..\pqauto-env\Scripts\python.exe -m pytest tests/ -q

# 3) Start dashboard
..\pqauto-env\Scripts\python.exe -m dashboard.app
```

Open http://127.0.0.1:5000

## Dashboard Usage

- Choose vehicle state
- Enter payload (or select HNDL mode)
- Execute OTA update
- Observe live stage pass/fail animation and verdict
- Track real-time metrics:
  - Blocked (Other)
  - Blocked (ECU)
  - Blocked (Replay)
  - Accepted (Valid)
  - Latest Request Total Time

## API Endpoints Used by UI

- GET /health
- GET /api/scenarios
- GET /api/hndl
- POST /api/run-json-scenario

## Notes

- This project is a security demo for hackathon and education workflows.
- For production, replace in-memory/demo stores with hardened persistent infrastructure.
