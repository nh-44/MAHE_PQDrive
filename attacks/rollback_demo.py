from vehicle.ota_server import OTAServer
from vehicle.gateway import VehicleGateway

class RollbackAttack:
    def __init__(self):
        self.server  = OTAServer()
        self.gateway = VehicleGateway(self.server.get_public_key())
        self._payload = None

    def set_payload(self, payload: bytes):
        self._payload = payload

    def run(self) -> dict:
        firmware = self._payload or b"[OEM-SIGNED] ADAS_ECU_FIRMWARE v1.0.0 WARNING:CONTAINS CVE-2024-3821 BUFFER-OVERFLOW"

        old_package = self.server.build_update_package(
            self.gateway.get_public_key(),
            current_version="2.0.0",
            incoming_version="1.0.0",
            firmware_blob=firmware,
        )
        result = self.gateway.receive_update(old_package)
        return {
            "attack":          "rollback",
            "blocked":         not result["all_passed"],
            "failed_at":       result["failed_at"],
            "payload_preview": firmware.decode(errors='replace')[:80],
            "why_blocked":     "The package is cryptographically perfect — real server signature, real hash. But incoming version 1.0.0 is not strictly greater than current version 2.0.0. The version monotonicity gate is independent of crypto and cannot be bypassed by having a valid signature.",
            "pqc_primitive":   "Version monotonicity (anti-rollback) — crypto stages all pass, blocked at stage 4",
            "pipeline":        result,
        }
