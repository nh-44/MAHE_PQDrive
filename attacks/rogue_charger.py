import os
import time
from vehicle.gateway import VehicleGateway
from vehicle.ota_server import OTAServer
from core.dilithium import generate_keypair as dil_keypair, sign
from core.kyber import encapsulate
from core.sha3_hash import hash_package

class RogueChargerAttack:
    def __init__(self):
        self.real_server  = OTAServer()
        self.gateway      = VehicleGateway(self.real_server.get_public_key())
        self.attacker_pub, self.attacker_priv = dil_keypair()
        self._payload = None

    def set_payload(self, payload: bytes):
        self._payload = payload

    def run(self) -> dict:
        fake_firmware = self._payload or (b"[MALWARE] BACKDOOR_PAYLOAD::REMOTE_ACCESS::CVE-2024-9999::" + os.urandom(16))
        ciphertext, session_key = encapsulate(self.gateway.get_public_key())
        package_hash    = hash_package(fake_firmware)
        forged_sig      = sign(self.attacker_priv, fake_firmware)

        evil_package = {
            "ciphertext":          ciphertext,
            "session_key":         session_key,
            "payload":             fake_firmware,
            "package_hash":        package_hash,
            "signature":           forged_sig,
            "current_version":     "1.0.0",
            "incoming_version":    "9.9.9",
            "timestamp":           time.time(),
            "target_ecu":          "ADAS",
            "charger_attestation": "invalid",  # Malicious charger provides invalid attestation
        }

        result = self.gateway.receive_update(evil_package)
        return {
            "attack":           "rogue_charger",
            "blocked":          not result["all_passed"],
            "failed_at":        result["failed_at"],
            "payload_preview":  fake_firmware.decode(errors='replace')[:80],
            "why_blocked":      "The rogue charger fails to present a valid attestation token at Gate 1 (Delivery Gate), short-circuiting the pipeline before executing any post-quantum cryptographic computations.",
            "pqc_primitive":    "Context-Aware Policy Gating (Gate 1)",
            "pipeline":         result,
        }

