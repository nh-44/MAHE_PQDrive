class ECUDomain:
    """
    Represents a logical domain of ECUs (e.g. ADAS, Powertrain, Body).
    After the gateway verifies a package, the domain controller applies
    the firmware update to its ECUs.
    """

    DOMAINS = ["ADAS", "Powertrain", "Body", "Chassis", "Infotainment"]

    def __init__(self, domain_name: str, initial_version: str = "1.0.0"):
        if domain_name not in self.DOMAINS:
            raise ValueError(f"Unknown domain '{domain_name}'. Choose from {self.DOMAINS}")
        self.domain_name = domain_name
        self.current_version = initial_version
        self.update_log = []

    def apply_update(self, incoming_version: str, payload: bytes) -> dict:
        """
        Simulate flashing the ECU domain with new firmware.
        In production this would write to secured flash memory.
        """
        result = {
            "domain":    self.domain_name,
            "from":      self.current_version,
            "to":        incoming_version,
            "bytes":     len(payload),
            "status":    "applied"
        }
        self.current_version = incoming_version
        self.update_log.append(result)
        return result

    def status(self) -> dict:
        return {
            "domain":  self.domain_name,
            "version": self.current_version,
            "updates": len(self.update_log)
        }
