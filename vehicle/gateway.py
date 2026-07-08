from core.kyber import generate_keypair as kyber_keypair
from core.pipeline import OTAVerificationPipeline

class VehicleGateway:
    """
    The vehicle-side secure gateway (think: Telematics Control Unit).
    Owns the vehicle's Kyber keypair. Receives OTA packages, runs the
    full 4-stage verification pipeline, and decides whether to forward
    to the ECU domain layer.
    """

    def __init__(self, server_public_key: bytes):
        self.kyber_pub, self.kyber_priv = kyber_keypair()
        self.server_public_key = server_public_key
        self.last_result = None

    def get_public_key(self) -> bytes:
        """Expose Kyber public key so OTA server can encapsulate to us."""
        return self.kyber_pub

    def receive_update(self, package: dict) -> dict:
        """
        Run the OTA verification pipeline on an incoming package.
        Returns the result dict from OTAVerificationPipeline.run().
        """
        pipeline = OTAVerificationPipeline(
            vehicle_public_key=self.kyber_pub,
            vehicle_private_key=self.kyber_priv,
            server_public_key=self.server_public_key,
        )
        self.last_result = pipeline.run(package)
        return self.last_result

    def is_verified(self) -> bool:
        return self.last_result is not None and self.last_result["all_passed"]
