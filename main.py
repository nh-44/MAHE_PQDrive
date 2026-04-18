from __future__ import annotations

from core.demo_runner import build_demo_report


def _print_result(title: str, result: dict) -> None:
	print(f"\n[{title}]")
	print(result)


def main() -> None:
	report = build_demo_report()
	print(f"\n=== {report['title']} ===")
	print("Threat Model:")
	print(report["threat_model"])
	print("\nPolicy:")
	print(report["policy"])

	for scenario in report["scenarios"]:
		_print_result(scenario["name"], scenario["result"])

	print("\n=== Summary Table ===")
	print(f"{'Scenario':<24} | {'Accepted':<8} | Failed At | Latency ms")
	print("-" * 78)
	for scenario in report["scenarios"]:
		print(
			f"{scenario['name']:<24} | "
			f"{str(scenario['accepted']):<8} | "
			f"{str(scenario['failed_at']):<12} | "
			f"{scenario['duration_ms']}"
		)

	print("\n=== Performance ===")
	print(report["metrics"])


if __name__ == "__main__":
	main()
