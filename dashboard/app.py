from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import time, re

from vehicle.ota_server import OTAServer
from vehicle.gateway import VehicleGateway
from vehicle.ecu_domain import ECUDomain
from vehicle.can_bus import CANBus
from vehicle.recovery import RecoveryManager
from core.dilithium import sign
from core.kyber import encapsulate
from core.sha3_hash import hash_package
from attacks.rogue_charger import RogueChargerAttack
from attacks.hndl_demo import HarvestNowDecryptLater
from attacks.rollback_demo import RollbackAttack
from attacks.tamper_demo import TamperAttack

app = Flask(__name__)
app.config["SECRET_KEY"] = "pq-auto-dev"
socketio = SocketIO(app, cors_allowed_origins="*")

server   = OTAServer()
gateway  = VehicleGateway(server.get_public_key())
domains  = {name: ECUDomain(name, "1.0.0") for name in ECUDomain.DOMAINS}
bus      = CANBus()
recovery = RecoveryManager()
event_log = []

def log_event(kind, msg, detail=None):
    entry = {"time": time.strftime("%H:%M:%S"), "kind": kind, "msg": msg, "detail": detail or {}}
    event_log.append(entry)
    socketio.emit("event", entry)

def extract_version(payload_str):
    m = re.search(r'SW:([\d]+\.[\d]+\.[\d]+)', payload_str)
    return m.group(1) if m else None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    return jsonify({"domains": [d.status() for d in domains.values()]})

@app.route("/api/simulate", methods=["POST"])
def simulate():
    data        = request.get_json()
    payload     = data.get("payload", "").strip()
    domain      = data.get("domain", "ADAS")
    version     = data.get("version", "2.0.0")
    attack_type = data.get("attack_type", "legitimate")

    payload_bytes = payload.encode() if payload else None
    ecu = domains.get(domain)

    # ── LEGITIMATE ──────────────────────────────────────────────
    if attack_type == "legitimate":
        current = ecu.current_version
        recovery.snapshot(domain, current, payload_bytes or b"snap")
        pkg    = server.build_update_package(
            gateway.get_public_key(), current, version, payload_bytes)
        result = gateway.receive_update(pkg)

        real_sig = sign(server.signing_priv, pkg["payload"])
        sha3     = hash_package(pkg["payload"])
        sk_hex   = pkg["session_key"][:16].hex()
        sig_hex  = real_sig[:32].hex()

        if result["all_passed"]:
            ecu.apply_update(version, pkg["payload"])
            bus.send("Gateway", domain, "OTA_APPLY", {"version": version})
            log_event("success", f"{domain} updated to {version}")
        return jsonify({
            "status":            "passed" if result["all_passed"] else "rejected",
            "pipeline":          result,
            "payload_preview":   payload[:120],
            "dilithium_sig_hex": sig_hex,
            "kyber_sk_hex":      sk_hex,
            "sha3_hash":         sha3,
            "sig_key_owner":     "OEM server Dilithium private key (verified ✓)",
        })

    # ── ROGUE CHARGER ────────────────────────────────────────────
    elif attack_type == "rogue_charger":
        atk = RogueChargerAttack()
        if payload_bytes:
            atk.set_payload(payload_bytes)
        result = atk.run()

        real_sig = sign(server.signing_priv,  payload_bytes or b"")
        atk_sig  = sign(atk.attacker_priv,    payload_bytes or b"")
        return jsonify({
            **result,
            "status":            "blocked",
            "dilithium_sig_hex": atk_sig[:32].hex(),
            "real_sig_hex":      real_sig[:32].hex(),
            "sig_key_owner":     "Attacker Dilithium keypair (NOT OEM server)",
            "sha3_hash":         hash_package(payload_bytes or b""),
            "kyber_sk_hex":      "encapsulated correctly (vehicle pubkey used)",
        })

    # ── ROLLBACK ─────────────────────────────────────────────────
    elif attack_type == "rollback":
        atk = RollbackAttack()
        if payload_bytes:
            atk.set_payload(payload_bytes)
        result = atk.run()
        real_sig = sign(server.signing_priv, payload_bytes or b"")
        return jsonify({
            **result,
            "status":            "blocked",
            "dilithium_sig_hex": real_sig[:32].hex(),
            "sig_key_owner":     "OEM server (signature IS valid — only version gate blocks this)",
            "sha3_hash":         hash_package(payload_bytes or b""),
            "kyber_sk_hex":      "valid",
        })

    # ── TAMPER ───────────────────────────────────────────────────
    elif attack_type == "tamper":
        atk = TamperAttack()
        if payload_bytes:
            atk.set_payload(payload_bytes)
        result = atk.run()

        real_sig = sign(server.signing_priv, payload_bytes or b"")
        tampered = bytearray(payload_bytes or b"x")
        mid = len(tampered) // 2
        inject = b" | INJECTED:0xFF3A "
        tampered[mid:mid+len(inject)] = inject
        return jsonify({
            **result,
            "status":            "blocked",
            "dilithium_sig_hex": real_sig[:32].hex(),
            "sig_key_owner":     "OEM server signed ORIGINAL — tampered bytes break signature",
            "sha3_hash":         hash_package(payload_bytes or b""),
            "tampered_hash":     hash_package(bytes(tampered)),
            "original_preview":  payload[:120],
            "tampered_preview":  bytes(tampered).decode(errors="replace")[:120],
        })

    # ── HNDL ─────────────────────────────────────────────────────
    elif attack_type == "hndl":
        result = HarvestNowDecryptLater().run()
        return jsonify({**result, "status": "resisted"})

    return jsonify({"error": "unknown attack type"}), 400

@app.route("/api/rollback/<domain_name>", methods=["POST"])
def do_rollback(domain_name):
    ecu = domains.get(domain_name)
    if not ecu:
        return jsonify({"error": "Unknown domain"}), 400
    result = recovery.rollback(ecu)
    bus.send("RecoveryManager", domain_name, "ROLLBACK", result)
    log_event("warn", f"Rollback on {domain_name}", result)
    return jsonify(result)

def create_app():
    return app, socketio
