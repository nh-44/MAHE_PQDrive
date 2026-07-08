import pytest
from vehicle.ota_server import OTAServer
from vehicle.gateway import VehicleGateway
from vehicle.ecu_domain import ECUDomain
from vehicle.recovery import RecoveryManager
from attacks.rogue_charger import RogueChargerAttack
from attacks.hndl_demo import HarvestNowDecryptLater
from attacks.rollback_demo import RollbackAttack
from attacks.tamper_demo import TamperAttack

@pytest.fixture
def server_and_gateway():
    server  = OTAServer()
    gateway = VehicleGateway(server.get_public_key())
    return server, gateway

def test_legitimate_update(server_and_gateway):
    server, gateway = server_and_gateway
    pkg    = server.build_update_package(gateway.get_public_key(), "1.0.0", "2.0.0")
    result = gateway.receive_update(pkg)
    assert result["all_passed"] is True
    assert result["failed_at"] is None

def test_rogue_charger_blocked():
    result = RogueChargerAttack().run()
    assert result["blocked"] is True
    assert result["failed_at"] == "delivery"

def test_hndl_resisted():
    result = HarvestNowDecryptLater().run()
    assert result["kyber_resists_hndl"] is True
    assert result["legitimate_decap_ok"] is True

def test_rollback_blocked():
    result = RollbackAttack().run()
    assert result["blocked"] is True
    assert result["failed_at"] == "version"

def test_tamper_blocked():
    result = TamperAttack().run()
    assert result["blocked"] is True
    assert result["failed_at"] == "dilithium"

def test_ecu_apply_and_rollback():
    ecu      = ECUDomain("ADAS", "1.0.0")
    recovery = RecoveryManager()
    recovery.snapshot("ADAS", "1.0.0", b"good_firmware")
    ecu.apply_update("2.0.0", b"new_firmware")
    assert ecu.current_version == "2.0.0"
    result = recovery.rollback(ecu)
    assert result["status"] == "rolled_back"
    assert ecu.current_version == "1.0.0"

def test_version_monotonicity(server_and_gateway):
    server, gateway = server_and_gateway
    pkg    = server.build_update_package(gateway.get_public_key(), "2.0.0", "1.0.0")
    result = gateway.receive_update(pkg)
    assert result["all_passed"] is False
    assert result["failed_at"] == "version"

def test_version_spoof_blocked(server_and_gateway):
    server, gateway = server_and_gateway
    # Build package with signed version = 1.0.0
    pkg = server.build_update_package(gateway.get_public_key(), "1.0.0", "1.0.0")
    # Attacker spoofs unauthenticated version header to bypass Gate 3
    pkg["incoming_version"] = "2.0.0"
    result = gateway.receive_update(pkg)
    assert result["all_passed"] is False
    assert result["failed_at"] == "version_spoof"

