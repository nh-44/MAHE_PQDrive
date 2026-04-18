#!/usr/bin/env python3
"""Final pre-hackathon validation script."""

import subprocess
import sys

def run_cmd(cmd, description):
    """Run command and report status."""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print('='*60)
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ PASS")
            if result.stdout:
                # Show key info only
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'passed' in line or 'ACCEPTED' in line or 'Summary' in line or 'Performance' in line:
                        print(f"   {line}")
            return True
        else:
            print(f"❌ FAIL")
            if result.stderr:
                print(result.stderr[:200])
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT (>30s)")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Run all validation checks."""
    print("\n" + "="*60)
    print("🚀 PQDrive Hackathon Pre-Submission Validation")
    print("="*60)
    
    checks = [
        ("..\\pqauto-env\\Scripts\\python.exe -m pytest -q tests/", "Test Suite (12 tests)"),
        ("..\\pqauto-env\\Scripts\\python.exe main.py 2>&1 | findstr 'Scenario_count\\|accepted_count\\|blocked_count'", "CLI Demo (7 scenarios)"),
        ("..\\pqauto-env\\Scripts\\python.exe -c \"from dashboard.app import app; from core.demo_runner import run_single_scenario; print('Dashboard imports OK')\"", "Dashboard Imports"),
        ("..\\pqauto-env\\Scripts\\python.exe -c \"from core.demo_runner import run_single_scenario; result = run_single_scenario('Legitimate OTA'); print(f'Interactive runner: {result[\"accepted\"]}'
)\"", "Interactive Runner"),
    ]
    
    results = []
    for cmd, desc in checks:
        results.append(run_cmd(cmd, desc))
    
    print("\n" + "="*60)
    print("📊 Final Summary")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    status_items = [
        ("Test Suite", results[0]),
        ("CLI Demo", results[1]),
        ("Dashboard", results[2]),
        ("Interactive", results[3]),
    ]
    
    for name, passed_check in status_items:
        symbol = "✅" if passed_check else "❌"
        print(f"{symbol} {name}")
    
    print(f"\n{'='*60}")
    print(f"Overall: {passed}/{total} checks passed")
    
    if passed == total:
        print("✅ READY FOR HACKATHON SUBMISSION")
        print("\nNext steps:")
        print("1. Review HACKATHON_GUIDE.md for demo script")
        print("2. Print handout (see HACKATHON_GUIDE.md)")
        print("3. Start dashboard: python -m flask -A dashboard.app run")
        print("4. Judges can access at http://localhost:5000")
        sys.exit(0)
    else:
        print(f"❌ ISSUES FOUND ({total - passed} failing)")
        sys.exit(1)

if __name__ == "__main__":
    main()
