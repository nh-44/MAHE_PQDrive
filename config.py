"""Configuration file for PQDrive demo."""

# Flask Dashboard Configuration
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True

# Charger Configuration
DEFAULT_CHARGER_NAME = "north-road-fast-charger"

# OTA Version Configuration
DEFAULT_CURRENT_VERSION = "1.0.0"
DEFAULT_NEW_VERSION = "2.0.0"
DEFAULT_TARGET_ECU = "maps_ecu"

# Safety-Critical ECU Configuration
SAFETY_CRITICAL_ECUS = [
    "braking_ecu",
    "steering_ecu",
    "adas_ecu",
    "powertrain_ecu"
]

# Infotainment ECU Configuration
INFOTAINMENT_ECUS = [
    "maps_ecu",
    "audio_ecu",
    "bluetooth_ecu"
]

# Vehicle State Defaults
DEFAULT_VEHICLE_STATE = {
    "charging_active": True,
    "data_link_locked": True,
    "battery_soc": 68,
    "speed_kph": 0,
    "thermal_state": "normal",
    "temperature_c": 31,
}

# Anti-Juice-Jacking Thresholds
MAX_SAFE_SPEED_KPH = 0
MIN_BATTERY_SOC = 20
MAX_SAFE_TEMPERATURE_C = 60
MAX_CLOCK_SKEW_SECONDS = 300

# Scenario Configuration
SCENARIOS = [
    "Legitimate OTA",
    "Trusted Charger OTA",
    "Anti-Juice Jacking",
    "Replay Attack",
    "Rogue Charger Attack",
    "Rollback Attack",
    "HNDL Resistance",
]

# Threat Injection Types
THREAT_TYPES = [
    "bit-flip",
    "downgrade",
    "tamper-signature",
]

# Log Verbosity Levels
LOG_LEVELS = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3,
    "CRITICAL": 4,
}

DEFAULT_LOG_LEVEL = "INFO"
