import unittest

from app.services.diagnostic_service import DiagnosticService
from app.services.obd_service import OBDReading, OBDTroubleCode
from app.services.vehicle_state_service import VehicleStateService


class _FakeObdService:
    def __init__(self, readings, codes):
        self._readings = readings
        self._codes = codes

    def read_live_data(self):
        return list(self._readings)

    def read_error_codes(self):
        return list(self._codes)

    def clear_error_codes(self):
        return True


class _FakeDatabase:
    def __init__(self):
        self.saved_measurements = []
        self.saved_history = []

    def save_measurement(self, data):
        self.saved_measurements.append(data)

    def save_history_snapshot(self, data, diagnostic_status, main_issue, diagnostic_summary, dtc_codes):
        self.saved_history.append(
            {
                "data": data,
                "diagnostic_status": diagnostic_status,
                "main_issue": main_issue,
                "diagnostic_summary": diagnostic_summary,
                "dtc_codes": dtc_codes,
            }
        )


class VehicleStateServiceTests(unittest.TestCase):
    def test_refresh_snapshot_uses_one_shared_analysis_result(self):
        readings = [
            OBDReading(name="RPM", value="4062", unit="rpm", key="rpm"),
            OBDReading(name="Vitesse", value="55", unit="km/h", key="speed"),
            OBDReading(name="Temperature moteur", value="28", unit="C", key="coolant_temp"),
            OBDReading(name="Batterie hybride SOC", value="57.3", unit="%", key="hybrid_soc"),
        ]
        codes = [OBDTroubleCode(code="P0301", description="Rates d'allumage cylindre 1", severity="Elevee")]
        database = _FakeDatabase()
        service = VehicleStateService(_FakeObdService(readings, codes), DiagnosticService(), database)

        snapshot = service.refresh_snapshot()

        self.assertEqual(snapshot.available_readings, 4)
        self.assertEqual(snapshot.dtc_count, 1)
        self.assertEqual(snapshot.overall_severity, DiagnosticService.CRITICAL)
        self.assertEqual(snapshot.metric_statuses["rpm"].label, "A surveiller")
        self.assertEqual(snapshot.primary_diagnostic.title, "Code DTC critique actif")
        self.assertEqual(len(database.saved_measurements), 1)
        self.assertEqual(len(database.saved_history), 1)


if __name__ == "__main__":
    unittest.main()
