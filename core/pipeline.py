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

		stage_started = perf_counter()
		result["kyber_ok"] = kyber.verify_session(
			self.vehicle_private_key,
			update_package["ciphertext"],
			update_package["session_key"],
		)
		result["stage_durations_ms"]["kyber"] = round((perf_counter() - stage_started) * 1000, 3)
		result["verification_trace"].append({"stage": "kyber", "ok": result["kyber_ok"], "duration_ms": result["stage_durations_ms"]["kyber"]})
		if not result["kyber_ok"]:
			result["failed_at"] = "kyber"
			return result

		stage_started = perf_counter()
		result["dilithium_ok"] = dilithium.verify(
			self.server_public_key,
			update_package["payload"],
			update_package["signature"],
		)
		result["stage_durations_ms"]["dilithium"] = round((perf_counter() - stage_started) * 1000, 3)
		result["verification_trace"].append({"stage": "dilithium", "ok": result["dilithium_ok"], "duration_ms": result["stage_durations_ms"]["dilithium"]})
		if not result["dilithium_ok"]:
			result["failed_at"] = "dilithium"
			return result

		stage_started = perf_counter()
		result["hash_ok"] = sha3_hash.verify_hash(
			update_package["payload"],
			update_package["package_hash"],
		)
		result["stage_durations_ms"]["hash"] = round((perf_counter() - stage_started) * 1000, 3)
		result["verification_trace"].append({"stage": "hash", "ok": result["hash_ok"], "duration_ms": result["stage_durations_ms"]["hash"]})
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
