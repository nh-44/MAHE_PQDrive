from vehicle.ota_server import OTAServer
from vehicle.gateway import VehicleGateway

class TamperAttack:
    def __init__(self):
        self.server  = OTAServer()
        self.gateway = VehicleGateway(self.server.get_public_key())
        self._payload = None

    def set_payload(self, payload: bytes):
        self._payload = payload

    def run(self) -> dict:
        original = self._payload or b"[OEM-SIGNED] ADAS_ECU_FIRMWARE v2.0.0 LANE-KEEP-ASSIST PATCH-SAFE"

        legit_package = self.server.build_update_package(
            self.gateway.get_public_key(),
            current_version="1.0.0",
            incoming_version="2.0.0",
            firmware_blob=original,
        )

        # MitM flips bytes
        tampered = bytearray(legit_package["payload"])
        tampered[0]  ^= 0xFF
        tampered[-1] ^= 0xFF
        # inject visible marker
        mid = len(tampered)//2
        inject = b"<<BACKDOOR_INJECTED>>"
        tampered[mid:mid+len(inject)] = inject
        legit_package["payload"] = bytes(tampered)

        result = self.gateway.receive_update(legit_package)
        return {
            "attack":           "payload_tamper",
            "blocked":          not result["all_passed"],
            "failed_at":        result["failed_at"],
            "original_preview": original.decode(errors='replace')[:80],
            "tampered_preview": bytes(tampered).decode(errors='replace')[:80],
            "why_blocked":      "The Dilithium signature was computed over the original bytes. Flipping even one bit changes the message digest entirely. verify(server_pubkey, tampered_payload, original_signature) returns False — the signature is no longer valid for this payload. SHA3-256 also independently catches it.",
            "pqc_primitive":    "CRYSTALS-Dilithium (FIPS 204) + SHA3-256 integrity check",
            "pipeline":         result,
        }
