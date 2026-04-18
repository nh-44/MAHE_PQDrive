from __future__ import annotations

from attacks.hndl_demo import run_hndl_demo
from attacks.rollback_demo import simulate_rollback_attack
from attacks.rogue_charger import simulate_rogue_charger_attack
from attacks.tamper_demo import simulate_tamper_attack
from core import dilithium, kyber
from vehicle.gateway import VehicleGateway
from vehicle.ota_server import OTAServer


def _print_result(title: str, result: dict) -> None:
	print(f"\n[{title}]")
	print(result)


def main() -> None:
	vehicle_public_key, vehicle_private_key = kyber.generate_keypair()
	server_public_key, server_private_key = dilithium.generate_keypair()

	server = OTAServer(
		server_private_key=server_private_key,
		server_public_key=server_public_key,
		vehicle_public_key=vehicle_public_key,
	)
	gateway = VehicleGateway(
		vehicle_public_key=vehicle_public_key,
		vehicle_private_key=vehicle_private_key,
		server_public_key=server_public_key,
	)

	legitimate_package = server.prepare_update(
		payload=b"firmware_v2",
		current_version="1.0.0",
		new_version="2.0.0",
	)
	legitimate_result = gateway.receive_update_request(legitimate_package)
	_print_result("Legitimate OTA", legitimate_result)

	rogue_result = simulate_rogue_charger_attack(gateway)
	_print_result("Rogue Charger Attack", rogue_result)

	hndl_result = run_hndl_demo()
	_print_result("HNDL Demo", hndl_result)

	rollback_result = simulate_rollback_attack(gateway, server)
	_print_result("Rollback Attack", rollback_result)

	tamper_result = simulate_tamper_attack(gateway, server)
	_print_result("Tamper Attack", tamper_result)

	print("\n=== Summary Table ===")
	print(f"{'Scenario':<24} | {'Accepted':<8} | Failed At")
	print("-" * 60)
	print(
		f"{'Legitimate OTA':<24} | "
		f"{str(legitimate_result.get('accepted', False)):<8} | "
		f"{legitimate_result.get('failed_at')}"
	)
	print(
		f"{'Rogue Charger Attack':<24} | "
		f"{str(rogue_result.get('accepted', False)):<8} | "
		f"{rogue_result.get('failed_at', rogue_result.get('reason'))}"
	)
	print(
		f"{'Rollback Attack':<24} | "
		f"{str(rollback_result.get('accepted', False)):<8} | "
		f"{rollback_result.get('failed_at')}"
	)
	print(
		f"{'Tamper Attack':<24} | "
		f"{str(tamper_result.get('accepted', False)):<8} | "
		f"{tamper_result.get('failed_at')}"
	)
	print(
		f"{'HNDL Demo (info)':<24} | "
		f"{'n/a':<8} | {'comparison only'}"
	)


if __name__ == "__main__":
	main()
