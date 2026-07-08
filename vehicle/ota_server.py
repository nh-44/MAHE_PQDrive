import os
import time
from core.dilithium import generate_keypair as dil_keypair, sign
from core.kyber import generate_keypair as kyber_keypair, encapsulate
from core.sha3_hash import hash_package

class OTAServer:
    def __init__(self):
        self.signing_pub, self.signing_priv = dil_keypair()

    def get_public_key(self) -> bytes:
        return self.signing_pub

    def build_update_package(
        self,
        vehicle_kyber_pub: bytes,
        current_version: str,
        incoming_version: str,
        firmware_blob: bytes = None
    ) -> dict:
        if firmware_blob is None:
            firmware_blob = (
                f"FIRMWARE::{incoming_version}::".encode()
                + os.urandom(64)
            )
        ciphertext, session_key = encapsulate(vehicle_kyber_pub)
        package_hash = hash_package(firmware_blob)
        signature = sign(self.signing_priv, firmware_blob)
        return {
            "ciphertext":          ciphertext,
            "session_key":         session_key,
            "payload":             firmware_blob,
            "package_hash":        package_hash,
            "signature":           signature,
            "current_version":     current_version,
            "incoming_version":    incoming_version,
            "timestamp":           time.time(),
            "target_ecu":          "ADAS",
            "charger_attestation": "valid",
        }

