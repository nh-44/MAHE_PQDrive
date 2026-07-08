import time
from core.kyber import verify_session
from core.dilithium import verify
from core.sha3_hash import verify_hash
from core.version_check import is_valid_version


class OTAVerificationPipeline:
    """
    Runs the 6-stage fail-fast post-quantum verification pipeline for automotive OTA updates.
    Fails fast at the earliest gate to minimize cryptographic CPU cycles on invalid packages.
    """

    def __init__(self, vehicle_public_key: bytes, vehicle_private_key: bytes, server_public_key: bytes):
        self.vehicle_public_key = vehicle_public_key
        self.vehicle_private_key = vehicle_private_key
        self.server_public_key = server_public_key

    def run(self, update_package: dict, vehicle_state: dict = None) -> dict:
        """
        Executes the 6 verification gates in sequential order:
        1. Delivery Gate (Operational context check)
        2. Freshness Gate (Replay window check)
        3. Target & Version Gate (Preliminary unauthenticated metadata check)
        4. Dilithium Gate (Asymmetric signature verification of origin)
        5. Kyber Gate (Asymmetric key encapsulation check)
        6. SHA3 & Authenticated Version Gate (Payload integrity & secure version binding check)
        """
        if vehicle_state is None:
            # Default simulated vehicle state (stationary, fully charged)
            vehicle_state = {
                "speed": 0,
                "battery": 100,
            }

        result = {
            "delivery_ok": False,
            "freshness_ok": False,
            "target_version_ok": False,
            "dilithium_ok": False,
            "kyber_ok": False,
            "hash_ok": False,
            "all_passed": False,
            "failed_at": None
        }

        # --- GATE 1: Delivery Gate (Context-Aware Gating) ---
        speed = vehicle_state.get("speed", 0)
        battery = vehicle_state.get("battery", 100)
        charger_attestation = update_package.get("charger_attestation", "valid")

        if speed != 0 or battery <= 5 or charger_attestation == "invalid":
            result["failed_at"] = "delivery"
            return result
        result["delivery_ok"] = True

        # --- GATE 2: Freshness Gate (Timestamp check) ---
        pkg_time = update_package.get("timestamp", time.time())
        current_time = time.time()
        # Enforce an acceptable skew window of 1 hour to block stale replayed frames
        if abs(current_time - pkg_time) > 3600:
            result["failed_at"] = "freshness"
            return result
        result["freshness_ok"] = True

        # --- GATE 3: Target and Version Gate (Unauthenticated check) ---
        # Check target domain mapping and preliminary version monotonicity to save CPU cycles
        target_ecu = update_package.get("target_ecu", "ADAS")
        current_ver = update_package.get("current_version", "1.0.0")
        incoming_ver = update_package.get("incoming_version", "1.0.0")

        version_ok = is_valid_version(current_ver, incoming_ver)
        if not version_ok:
            result["failed_at"] = "version"
            return result
        result["target_version_ok"] = True

        # --- GATE 4: Dilithium Gate (ML-DSA-44 Signature Verification) ---
        # Verifies that the package was signed by the OEM server
        dilithium_ok = verify(
            self.server_public_key,
            update_package["payload"],
            update_package["signature"]
        )
        result["dilithium_ok"] = dilithium_ok
        if not dilithium_ok:
            result["failed_at"] = "dilithium"
            return result

        # --- GATE 5: Kyber Gate (ML-KEM-512 Decapsulation) ---
        # Recovers and verifies the symmetric session key
        kyber_ok = verify_session(
            self.vehicle_private_key,
            update_package["ciphertext"],
            update_package["session_key"]
        )
        result["kyber_ok"] = kyber_ok
        if not kyber_ok:
            result["failed_at"] = "kyber"
            return result

        # --- GATE 6: SHA3 Integrity & Authenticated Version Check ---
        # 1. Payload hash check (Integrity)
        hash_ok = verify_hash(
            update_package["payload"],
            update_package["package_hash"]
        )
        result["hash_ok"] = hash_ok
        if not hash_ok:
            result["failed_at"] = "hash"
            return result

        # 2. Secure Version Binding (Fix for unauthenticated header spoofing vulnerability)
        # Extract the version number embedded inside the signed payload to verify authenticity
        try:
            payload_str = update_package["payload"]
            if b"FIRMWARE::" in payload_str:
                parts = payload_str.split(b"::")
                authenticated_ver = parts[1].decode("utf-8")
                if authenticated_ver != incoming_ver:
                    # Reject because the header version was spoofed to bypass Gate 3
                    result["failed_at"] = "version_spoof"
                    return result
        except Exception:
            result["failed_at"] = "version_spoof"
            return result

        result["all_passed"] = True
        return result