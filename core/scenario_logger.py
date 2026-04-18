"""Scenario logging system for chain-of-thought execution tracing."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3


class ScenarioLogger:
    """Captures real-time logs of scenario execution for visualization."""

    def __init__(self, scenario_name: str) -> None:
        self.scenario_name = scenario_name
        self.logs: list[dict] = []
        self.start_time = datetime.now()
        self._log("START", f"Scenario: {scenario_name}", LogLevel.INFO)

    def _log(self, stage: str, message: str, level: LogLevel = LogLevel.INFO) -> None:
        """Add a log entry to the chain."""
        elapsed_ms = (datetime.now() - self.start_time).total_seconds() * 1000
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "elapsed_ms": round(elapsed_ms, 2),
            "stage": stage,
            "message": message,
            "level": level.name,
        })

    def log_condition(self, label: str, value: Any, passed: bool = True) -> None:
        """Log a condition check."""
        status = "✓ PASS" if passed else "✗ FAIL"
        self._log(
            "CONDITION",
            f"{label}: {value} → {status}",
            LogLevel.INFO if passed else LogLevel.ERROR,
        )

    def log_check(self, check_name: str, passed: bool, reason: str = "") -> None:
        """Log a security check result."""
        status = "✓ ACCEPTED" if passed else "✗ REJECTED"
        msg = f"{check_name}: {status}"
        if reason:
            msg += f" ({reason})"
        self._log(
            "CHECK",
            msg,
            LogLevel.INFO if passed else LogLevel.WARNING,
        )

    def log_crypto_operation(self, operation: str, duration_ms: float, success: bool = True) -> None:
        """Log cryptographic operation."""
        status = "✓ OK" if success else "✗ FAILED"
        msg = f"{operation}: {status} [{duration_ms:.3f}ms]"
        self._log(
            "CRYPTO",
            msg,
            LogLevel.INFO if success else LogLevel.ERROR,
        )

    def log_decision(self, decision: str, accepted: bool) -> None:
        """Log the final decision."""
        status = "ACCEPTED" if accepted else "BLOCKED"
        self._log(
            "DECISION",
            f"Update {status}: {decision}",
            LogLevel.INFO if accepted else LogLevel.WARNING,
        )

    def log_defense(self, defense_name: str, attack: str, blocked: bool = True) -> None:
        """Log defense mechanism activation."""
        if blocked:
            self._log(
                "DEFENSE",
                f"{defense_name} blocked: {attack}",
                LogLevel.WARNING,
            )
        else:
            self._log(
                "DEFENSE",
                f"{defense_name} passed: {attack}",
                LogLevel.INFO,
            )

    def log_state_transition(self, from_state: str, to_state: str) -> None:
        """Log state change."""
        self._log(
            "STATE",
            f"{from_state} → {to_state}",
            LogLevel.DEBUG,
        )

    def log_error(self, error_stage: str, error_message: str) -> None:
        """Log an error."""
        self._log(
            "ERROR",
            f"{error_stage}: {error_message}",
            LogLevel.ERROR,
        )

    def finalize(self) -> None:
        """Mark the scenario as complete."""
        total_time_ms = (datetime.now() - self.start_time).total_seconds() * 1000
        self._log(
            "COMPLETE",
            f"Scenario completed in {total_time_ms:.2f}ms",
            LogLevel.INFO,
        )

    def get_logs(self) -> list[dict]:
        """Return all logs as structured data."""
        return self.logs

    def get_text_log(self) -> str:
        """Return logs as formatted text."""
        lines = [f"=== {self.scenario_name} Execution Log ==="]
        for log in self.logs:
            prefix = log["level"][0]  # D, I, W, E
            time_str = log["elapsed_ms"]
            stage = log["stage"].ljust(12)
            msg = log["message"]
            lines.append(f"[{prefix}] {time_str:>7.2f}ms | {stage} | {msg}")
        return "\n".join(lines)

    def get_chain_of_thought(self) -> str:
        """Return a chain-of-thought summary."""
        lines = [f"\n=== Chain of Thought: {self.scenario_name} ==="]
        lines.append(f"Started: {self.start_time.strftime('%H:%M:%S.%f')[:-3]}")
        lines.append("")

        # Group by stage
        stages = {}
        for log in self.logs:
            stage = log["stage"]
            if stage not in stages:
                stages[stage] = []
            stages[stage].append(log)

        # Print by stage
        for stage_name in ["START", "CONDITION", "CHECK", "CRYPTO", "DEFENSE", "DECISION", "ERROR", "COMPLETE"]:
            if stage_name in stages:
                lines.append(f"\n[{stage_name}]")
                for log in stages[stage_name]:
                    lines.append(f"  • {log['message']}")

        return "\n".join(lines)
