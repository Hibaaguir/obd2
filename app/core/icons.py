from pathlib import Path


ICON_DIR = Path(__file__).resolve().parents[2] / "assets" / "icons"

PHOSPHOR_ICON_MAP = {
    "access-point": "broadcast.svg",
    "alert-outline": "warning.svg",
    "battery-high": "battery-high.svg",
    "car-battery": "car-battery.svg",
    "car-speed-limiter": "gauge.svg",
    "chart-line": "chart-line.svg",
    "check-circle-outline": "check-circle.svg",
    "clipboard-pulse-outline": "heartbeat.svg",
    "clock-outline": "clock.svg",
    "close-circle-outline": "x-circle.svg",
    "connection": "plugs-connected.svg",
    "counter": "gauge.svg",
    "current-dc": "lightning.svg",
    "delete-outline": "trash.svg",
    "engine-outline": "engine.svg",
    "fan": "fan.svg",
    "file-document-outline": "file-text.svg",
    "fuel": "gas-pump.svg",
    "gauge": "gauge.svg",
    "history": "clock-counter-clockwise.svg",
    "identifier": "identification-card.svg",
    "information-outline": "info.svg",
    "magnify-scan": "magnifying-glass.svg",
    "refresh": "arrow-clockwise.svg",
    "rotate-3d-variant": "arrows-clockwise.svg",
    "shield-check-outline": "shield-check.svg",
    "speedometer": "gauge.svg",
    "thermometer": "thermometer.svg",
    "thermometer-lines": "thermometer-simple.svg",
    "weather-sunny": "sun.svg",
    "wifi": "wifi-high.svg",
}


def icon_path(icon_name: str) -> Path | None:
    filename = PHOSPHOR_ICON_MAP.get(icon_name)
    if not filename:
        return None
    return ICON_DIR / filename
