"""
Phase 7B: Demo Attack Scenarios - Test attacks through REAL gateway

This module demonstrates how the OTA security pipeline defends against attacks.
Unlike previous demos that were simulated, these scenarios:
1. Create malicious OTA packages
2. Inject specific attacks
3. Submit through the REAL vehicle gateway
4. Verify gateway rejection

Run with: python demo_attack_scenarios.py
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from core import dilithium, kyber
from core.pipeline import OTAVerificationPipeline
from vehicle.gateway import VehicleGateway
from vehicle.ota_server import OTAServer


class RealGatewayAttackTester:
    """Test attack scenarios through the real vehicle gateway."""
    
    def __init__(self):
        """Initialize crypto keys and gateway."""
        # Generate keys for testing
        self.server_pub, self.server_priv = dilithium.generate_keypair()
        self.vehicle_pub, self.vehicle_priv = kyber.generate_keypair()
        
        # Initialize OTA server (for creating packages)
        self.ota_server = OTAServer(
            server_private_key=self.server_priv,
            server_public_key=self.server_pub,
            vehicle_public_key=self.vehicle_pub,
        )
        
        # Initialize real gateway (for validating packages)
        self.gateway = VehicleGateway(
            vehicle_public_key=self.vehicle_pub,
            vehicle_private_key=self.vehicle_priv,
            server_public_key=self.server_pub,
        )
        
        self.results = []
    
    def _create_clean_package(self, payload_text: str = "TEST_FIRMWARE_v2.0.0", target_ecu: str = "maps_ecu") -> dict:
        """Create a clean OTA package signed by server."""
        return self.ota_server.prepare_update(
            payload=payload_text.encode(),
            current_version="1.0.0",
            new_version="2.0.0",
            target_ecu=target_ecu,
        )
    
    def _submit_to_gateway(self, package: dict, test_name: str) -> dict:
        """Submit package to real gateway and capture result."""
        try:
            # Add request metadata for tracking
            package["request_id"] = f"attack_test_{test_name}_{datetime.now().timestamp()}"
            # Use valid source that gateway accepts
            if "source" not in package:
                package["source"] = "legitimate_ota_server"
            
            # Submit through REAL gateway
            result = self.gateway.receive_update_request(package)
            return {
                "test": test_name,
                "status": "submitted",
                "gateway_response": result,
                "blocked": not result.get("accepted", False),
            }
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return {
                "test": test_name,
                "status": "error",
                "error": str(e),
                "traceback": tb,
                "blocked": True,  # Error = rejection
            }
    
    def attack_bit_flip(self) -> dict:
        """
        ATTACK: Bit-flip in encrypted payload
        DEFENSE: AEAD authentication will fail
        """
        clean = self._create_clean_package()
        
        # Flip a bit in the encrypted payload
        encrypted = bytes.fromhex(clean["encrypted_payload"])
        mutated = bytearray(encrypted)
        mutated[0] ^= 0x01  # Flip single bit
        clean["encrypted_payload"] = mutated.hex()
        
        result = self._submit_to_gateway(clean, "bit-flip")
        result["description"] = "Bitflip in AEAD ciphertext fails authentication"
        result["expected"] = "blocked"
        result["passes"] = result["blocked"]
        return result
    
    def attack_signature_tamper(self) -> dict:
        """
        ATTACK: Tamper with Dilithium signature
        DEFENSE: Signature verification fails
        """
        clean = self._create_clean_package()
        
        # Corrupt signature
        sig = bytes.fromhex(clean["signature"])
        mutated = bytearray(sig)
        mutated[0] ^= 0xFF  # Flip all bits in first byte
        clean["signature"] = mutated.hex()
        
        result = self._submit_to_gateway(clean, "signature-tamper")
        result["description"] = "Tampered Dilithium signature fails verification"
        result["expected"] = "blocked"
        result["passes"] = result["blocked"]
        return result
    
    def attack_version_downgrade(self) -> dict:
        """
        ATTACK: Request firmware downgrade
        DEFENSE: Version check fails (current >= requested)
        """
        clean = self._create_clean_package()
        
        # Downgrade version
        clean["incoming_version"] = "0.5.0"  # Lower than current 1.0.0
        
        result = self._submit_to_gateway(clean, "version-downgrade")
        result["description"] = "Downgrade attempt rejected by version check"
        result["expected"] = "blocked"
        result["passes"] = result["blocked"]
        return result
    
    def attack_expired_package(self) -> dict:
        """
        ATTACK: Submit expired OTA package
        DEFENSE: Freshness check rejects expired timestamps
        """
        clean = self._create_clean_package()
        
        # Set expiry to past
        clean["expires_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        
        result = self._submit_to_gateway(clean, "expired-package")
        result["description"] = "Expired package rejected by freshness check"
        result["expected"] = "blocked"
        result["passes"] = result["blocked"]
        return result
    
    def attack_future_dated_package(self) -> dict:
        """
        ATTACK: Submit future-dated package (time travel attack)
        DEFENSE: Freshness check rejects future timestamps
        """
        clean = self._create_clean_package()
        
        # Set issued_at to future
        clean["issued_at"] = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        
        result = self._submit_to_gateway(clean, "future-dated-package")
        result["description"] = "Future-dated package rejected by freshness check"
        result["expected"] = "blocked"
        result["passes"] = result["blocked"]
        return result
    
    def attack_replay(self) -> dict:
        """
        ATTACK: Replay the same request twice
        DEFENSE: Persistent replay tracking blocks second submission
        """
        clean = self._create_clean_package()
        request_id = f"replay_test_{datetime.now().timestamp()}"
        clean["request_id"] = request_id
        # Note: source already set to "legitimate_ota_server" in _create_clean_package
        
        # First submission - should succeed
        result1 = self._submit_to_gateway(clean, "replay-first")
        accepted_first = result1.get("gateway_response", {}).get("accepted", False)
        
        # Second submission with SAME request_id - should be rejected
        result2 = self._submit_to_gateway(clean, "replay-second")
        blocked_second = not result2.get("gateway_response", {}).get("accepted", False)
        
        return {
            "test": "replay-attack",
            "description": "Identical request rejected on second submission",
            "expected": "first-accepted-then-blocked",
            "first_submission": result1,
            "second_submission": result2,
            "passes": accepted_first and blocked_second,
            "blocked": blocked_second,
        }
    
    def attack_unsigned_firmware(self) -> dict:
        """
        ATTACK: Submit firmware with missing Kyber ciphertext
        DEFENSE: Kyber verification fails (missing encapsulation)
        """
        clean = self._create_clean_package()
        
        # Remove Kyber ciphertext (simulating unsigned FW)
        clean.pop("ciphertext", None)
        
        result = self._submit_to_gateway(clean, "unsigned-firmware")
        result["description"] = "Missing Kyber ciphertext fails encapsulation check"
        result["expected"] = "blocked"
        result["passes"] = result["blocked"]
        return result
    
    def attack_wrong_target_ecu(self) -> dict:
        """
        ATTACK: Submit firmware for wrong target ECU (MAPS firmware to AUDIO)
        DEFENSE: ECU_ID mismatch in policy check
        """
        clean = self._create_clean_package(target_ecu="maps_ecu")
        
        # Change target ECU to a different valid ECU (but firmware was for MAPS)
        # This simulates applying MAPS firmware to AUDIO ECU
        clean["target_ecu"] = "audio_ecu"  # But payload was prepared for maps_ecu
        
        result = self._submit_to_gateway(clean, "wrong-target-ecu")
        result["description"] = "ECU mismatch between target and firmware payload"
        result["expected"] = "blocked"
        result["passes"] = result["blocked"]
        return result
    
    def scenario_valid_firmware(self) -> dict:
        """
        SCENARIO: Valid firmware update (should PASS)
        This verifies the happy path works correctly
        """
        clean = self._create_clean_package()
        
        result = self._submit_to_gateway(clean, "valid-firmware")
        result["description"] = "Valid firmware passes all checks"
        result["expected"] = "accepted"
        result["passes"] = result.get("gateway_response", {}).get("accepted", False)
        return result
    
    def run_all_tests(self) -> dict:
        """Run all attack scenarios and return comprehensive results."""
        print("\n" + "="*70)
        print("PHASE 7B: DEMO ATTACK SCENARIOS - REAL GATEWAY TESTING")
        print("="*70 + "\n")
        
        tests = [
            ("Valid Firmware (Happy Path)", self.scenario_valid_firmware),
            ("Bit-Flip Attack", self.attack_bit_flip),
            ("Signature Tampering", self.attack_signature_tamper),
            ("Version Downgrade", self.attack_version_downgrade),
            ("Expired Package", self.attack_expired_package),
            ("Future-Dated Package", self.attack_future_dated_package),
            ("Replay Attack", self.attack_replay),
            ("Unsigned Firmware", self.attack_unsigned_firmware),
            ("Wrong Target ECU", self.attack_wrong_target_ecu),
        ]
        
        results = []
        passed_count = 0
        failed_count = 0
        
        for test_name, test_func in tests:
            print(f"Running: {test_name}...", end=" ")
            try:
                result = test_func()
                results.append(result)
                
                # Check if test passed expectations
                test_passed = result.get("passes", False)
                if test_passed:
                    print("[PASS]")
                    passed_count += 1
                else:
                    print("[FAIL]")
                    failed_count += 1
                    
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                print(f"[ERROR] {e}")
                print(tb)
                results.append({
                    "test": test_name,
                    "error": str(e),
                    "traceback": tb,
                    "passes": False,
                })
                failed_count += 1
        
        print("\n" + "="*70)
        print(f"RESULTS: {passed_count} passed, {failed_count} failed")
        print("="*70 + "\n")
        
        # Save detailed results
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test_suite": "Phase 7B - Real Gateway Attack Scenarios",
            "total_tests": len(tests),
            "passed": passed_count,
            "failed": failed_count,
            "success_rate": f"{(passed_count / len(tests) * 100):.1f}%",
            "results": results,
        }
        
        return report


def main():
    """Run demo attack scenarios and save results."""
    tester = RealGatewayAttackTester()
    results = tester.run_all_tests()
    
    # Save results to JSON
    output_file = Path("demo_attack_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
        print(f"[INFO] Results saved to: {output_file}\n")
        
        # Print summary
        print("ATTACK SCENARIO SUMMARY")
        print("-" * 70)
        for result in results["results"]:
            test_name = result.get("test", "unknown")
            description = result.get("description", "")
            status = "[PASS]" if result.get("passes", False) else "[FAIL]"
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
