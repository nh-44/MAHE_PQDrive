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
