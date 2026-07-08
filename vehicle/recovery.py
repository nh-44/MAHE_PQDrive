class RecoveryManager:
    """
    Handles failed OTA update scenarios.
    Stores a golden (last-known-good) snapshot per ECU domain so we can
    roll back safely if verification or flashing fails.
    """

    def __init__(self):
        self.snapshots = {}   # domain_name -> {"version": str, "payload": bytes}

    def snapshot(self, domain_name: str, version: str, payload: bytes):
        """Save a known-good state before attempting an update."""
        self.snapshots[domain_name] = {
            "version": version,
            "payload": payload,
        }

    def rollback(self, ecu_domain) -> dict:
        """
        Restore an ECU domain to its last snapshot.
        Returns a result dict.
        """
        name = ecu_domain.domain_name
        if name not in self.snapshots:
            return {"status": "error", "reason": f"No snapshot found for domain '{name}'"}

        snap = self.snapshots[name]
        ecu_domain.current_version = snap["version"]
        return {
            "status":   "rolled_back",
            "domain":   name,
            "restored": snap["version"],
        }

    def has_snapshot(self, domain_name: str) -> bool:
        return domain_name in self.snapshots
