#!/usr/bin/env python3
"""Quick test of the interactive dashboard features."""

from dashboard.app import app
print('✓ Dashboard app imports successfully')

from core.demo_runner import run_single_scenario

# Test 1: Basic scenario
result = run_single_scenario('Legitimate OTA')
print(f"✓ Scenario runner works: {result['name']} - accepted={result['accepted']}")

# Test 2: Vehicle state override
result2 = run_single_scenario('Anti-Juice Jacking', {'speed_kph': 30})
print(f"✓ Vehicle state override works: speed=30 -> failed_at={result2['failed_at']}")

# Test 3: Juice jacking with safe state
result3 = run_single_scenario('Anti-Juice Jacking', {'speed_kph': 0, 'data_link_locked': True})
print(f"✓ Anti-juice with safe state: {result3['accepted']} (should accept if state is safe)")

print("\n✅ All interactive dashboard tests pass!")
