from typing import Any

from app.core.elm_pid_registry import PID_BY_KEY
from app.services.obd_service import OBDReading


def measurement_from_readings(readings: list[OBDReading]) -> dict[str, Any]:
    measurement: dict[str, Any] = {"raw_data": {}}
    for reading in readings:
        pid = PID_BY_KEY.get(reading.key)
        if not pid:
            continue
        measurement["raw_data"][reading.key] = {
            "label": reading.name,
            "value": reading.value,
            "unit": reading.unit,
            "available": reading.available,
            "raw_response": reading.raw_response,
        }
        if reading.available:
            measurement[pid.storage_field] = reading.value
    return measurement
