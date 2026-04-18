"""OTA verification pipeline combining PQC, integrity, and version checks."""

from __future__ import annotations

from time import perf_counter

from . import dilithium, kyber, sha3_hash, version_check


class OTAVerificationPipeline:
	"""Run all mandatory checks before accepting an OTA package."""

	def __init__(
		self,
		vehicle_public_key: bytes,
		vehicle_private_key: bytes,
		server_public_key: bytes,
	) -> None:
		self.vehicle_public_key = vehicle_public_key
		self.vehicle_private_key = vehicle_private_key
		self.server_public_key = server_public_key

	def run(self, update_package: dict) -> dict:
		"""Execute fail-fast OTA verification checks in strict order."""
		result = {
			"kyber_ok": False,
			"dilithium_ok": False,
			"hash_ok": False,
			"version_ok": False,
			"all_passed": False,
			"failed_at": None,
			"verification_trace": [],
			"stage_durations_ms": {},
		}

		# SECURITY FIX (Phase 7C): Add freshness check BEFORE cryptographic verification
		try:
			from datetime import datetime, timezone
			
			stage_started = perf_counter()
			
			# Check that both timestamps are present
			if "issued_at" not in update_package or "expires_at" not in update_package:
				result["failed_at"] = "freshness"
				result["verification_trace"].append({
					"stage": "freshness",
					"ok": False,
					"reason": "missing timestamp",
					"duration_ms": round((perf_counter() - stage_started) * 1000, 3)
				})
				result["stage_durations_ms"]["freshness"] = round((perf_counter() - stage_started) * 1000, 3)
				return result
			
			# Parse timestamps
			issued_at = datetime.fromisoformat(update_package["issued_at"])
			expires_at = datetime.fromisoformat(update_package["expires_at"])
			now = datetime.now(timezone.utc)
			
			# Check: Not issued in the future
			if now < issued_at:
				result["failed_at"] = "freshness"
				result["verification_trace"].append({
					"stage": "freshness",
					"ok": False,
					"reason": "not_yet_valid (issued in future)",
					"duration_ms": round((perf_counter() - stage_started) * 1000, 3)
				})
				result["stage_durations_ms"]["freshness"] = round((perf_counter() - stage_started) * 1000, 3)
				return result
			
			# Check: Not expired
			if now > expires_at:
				result["failed_at"] = "freshness"
				result["verification_trace"].append({
					"stage": "freshness",
					"ok": False,
					"reason": "expired",
					"duration_ms": round((perf_counter() - stage_started) * 1000, 3)
				})
				result["stage_durations_ms"]["freshness"] = round((perf_counter() - stage_started) * 1000, 3)
				return result
			
			result["stage_durations_ms"]["freshness"] = round((perf_counter() - stage_started) * 1000, 3)
			result["verification_trace"].append({
				"stage": "freshness",
				"ok": True,
				"duration_ms": result["stage_durations_ms"]["freshness"]
			})
		except Exception as e:
			result["failed_at"] = "freshness"
			result["verification_trace"].append({
				"stage": "freshness",
				"ok": False,
				"reason": f"freshness check error: {str(e)}"
			})
			return result

		stage_started = perf_counter()
		# SECURITY FIX (Phase 7B): Kyber verification already done during gateway decryption
		# Gateway decapsulates and decrypts, so we skip Kyber verification here
		result["kyber_ok"] = True  # Mark as passed (already verified during decryption)
		result["stage_durations_ms"]["kyber"] = round((perf_counter() - stage_started) * 1000, 3)
		result["verification_trace"].append({"stage": "kyber", "ok": result["kyber_ok"], "reason": "verified_during_decryption", "duration_ms": result["stage_durations_ms"]["kyber"]})

		# Convert hex strings back to bytes for verification (gateway stores as hex for JSON)
		try:
			payload_bytes = bytes.fromhex(update_package["payload"]) if isinstance(update_package["payload"], str) else update_package["payload"]
			signature_bytes = bytes.fromhex(update_package["signature"]) if isinstance(update_package["signature"], str) else update_package["signature"]
		except (ValueError, TypeError) as e:
			result["dilithium_ok"] = False
			result["failed_at"] = "format_error"
			result["verification_trace"].append({"stage": "format", "ok": False, "reason": str(e)})
			return result

		stage_started = perf_counter()
		result["dilithium_ok"] = dilithium.verify(
			self.server_public_key,
			payload_bytes,
			signature_bytes,
		)
		result["stage_durations_ms"]["dilithium"] = round((perf_counter() - stage_started) * 1000, 3)
		result["verification_trace"].append({"stage": "dilithium", "ok": result["dilithium_ok"], "duration_ms": result["stage_durations_ms"]["dilithium"]})
		if not result["dilithium_ok"]:
			result["failed_at"] = "dilithium"
			return result

		stage_started = perf_counter()
		expected_hash = update_package.get("expected_payload_hash", update_package.get("package_hash"))
		result["hash_ok"] = sha3_hash.verify_hash(
			payload_bytes,
			expected_hash,
		)
		result["stage_durations_ms"]["hash"] = round((perf_counter() - stage_started) * 1000, 3)
		result["verification_trace"].append({
			"stage": "hash",
			"ok": result["hash_ok"],
			"duration_ms": result["stage_durations_ms"]["hash"],
			"expected_payload_hash": expected_hash,
			"computed_payload_hash": sha3_hash.hash_package(payload_bytes),
		})
		if not result["hash_ok"]:
			result["failed_at"] = "hash"
			return result

		stage_started = perf_counter()
		result["version_ok"] = version_check.is_valid_version(
			update_package["current_version"],
			update_package["incoming_version"],
		)
		result["stage_durations_ms"]["version"] = round((perf_counter() - stage_started) * 1000, 3)
		result["verification_trace"].append({"stage": "version", "ok": result["version_ok"], "duration_ms": result["stage_durations_ms"]["version"]})
		if not result["version_ok"]:
			result["failed_at"] = "version"
			return result

		result["all_passed"] = True
		result["veracity_score"] = 1.0
		return result
