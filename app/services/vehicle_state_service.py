from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.measurement_mapper import measurement_from_readings
from app.services.diagnostic_service import DiagnosticResult, DiagnosticService
from app.services.obd_service import OBDReading, OBDService, OBDTroubleCode


@dataclass(frozen=True)
class MetricStatus:
    key: str
    label: str
    severity: str


@dataclass(frozen=True)
class VehicleSnapshot:
    timestamp: str
    readings: list[OBDReading]
    codes: list[OBDTroubleCode]
    diagnostics: list[DiagnosticResult]
    overall_severity: str
    metric_statuses: dict[str, MetricStatus]
    measurement_data: dict[str, object]

    @property
    def available_readings(self) -> int:
        return sum(1 for reading in self.readings if reading.available)

    @property
    def total_readings(self) -> int:
        return len(self.readings)

    @property
    def dtc_count(self) -> int:
        return len(self.codes)

    @property
    def primary_diagnostic(self) -> DiagnosticResult | None:
        for diagnostic in self.diagnostics:
            if diagnostic.severity != DiagnosticService.NORMAL:
                return diagnostic
        return self.diagnostics[0] if self.diagnostics else None

    @property
    def live_diagnostics(self) -> list[DiagnosticResult]:
        return [
            item for item in self.diagnostics if not item.title.lower().startswith("code dtc")
        ]

    @property
    def dtc_diagnostic(self) -> DiagnosticResult | None:
        return next(
            (item for item in self.diagnostics if item.title.lower().startswith("code dtc")),
            None,
        )


class VehicleStateService:
    def __init__(self, obd_service: OBDService, diagnostic_service: DiagnosticService, database=None):
        self.obd_service = obd_service
        self.diagnostic_service = diagnostic_service
        self.database = database
        self._latest_snapshot: VehicleSnapshot | None = None

    @property
    def latest_snapshot(self) -> VehicleSnapshot | None:
        return self._latest_snapshot

    def refresh_snapshot(self) -> VehicleSnapshot:
        readings = self.obd_service.read_live_data()
        codes = self.obd_service.read_error_codes()
        snapshot = self.build_snapshot(readings, codes)
        self._latest_snapshot = snapshot
        self._persist_snapshot(snapshot)
        return snapshot

    def clear_codes_and_refresh(self) -> VehicleSnapshot:
        success = self.obd_service.clear_error_codes()
        if not success:
            raise RuntimeError("Effacement non confirme par l'ECU.")
        return self.refresh_snapshot()

    def build_snapshot(
        self,
        readings: list[OBDReading],
        codes: list[OBDTroubleCode],
        timestamp: str | None = None,
    ) -> VehicleSnapshot:
        snapshot_time = timestamp or datetime.now().isoformat(timespec="seconds")
        diagnostics = self.diagnostic_service.analyze(readings, codes)
        overall = self.diagnostic_service.overall_severity(diagnostics)
        measurement_data = measurement_from_readings(readings)
        measurement_data["timestamp"] = snapshot_time

        return VehicleSnapshot(
            timestamp=snapshot_time,
            readings=readings,
            codes=codes,
            diagnostics=diagnostics,
            overall_severity=overall,
            metric_statuses=self._metric_statuses(readings),
            measurement_data=measurement_data,
        )

    def _persist_snapshot(self, snapshot: VehicleSnapshot):
        if self.database is None:
            return

        self.database.save_measurement(snapshot.measurement_data)
        primary = snapshot.primary_diagnostic
        self.database.save_history_snapshot(
            snapshot.measurement_data,
            diagnostic_status=snapshot.overall_severity,
            main_issue=primary.title if primary else "Etat normal",
            diagnostic_summary=primary.message if primary else "Aucune anomalie detectee avec les donnees disponibles.",
            dtc_codes=snapshot.codes,
        )

    @classmethod
    def _metric_statuses(cls, readings: list[OBDReading]) -> dict[str, MetricStatus]:
        statuses: dict[str, MetricStatus] = {}
        for reading in readings:
            label, severity = cls._metric_status(reading)
            statuses[reading.key] = MetricStatus(reading.key, label, severity)
        return statuses

    @classmethod
    def _metric_status(cls, reading: OBDReading) -> tuple[str, str]:
        if not reading.available:
            return "Non supporte", DiagnosticService.NORMAL

        if reading.key == "speed":
            numeric = cls._to_float(reading.value)
            if numeric is None:
                return "En attente", DiagnosticService.NORMAL
            if numeric <= 5:
                return "Stable", DiagnosticService.NORMAL
            if numeric < 110:
                return "Normal", DiagnosticService.NORMAL
            return "A surveiller", DiagnosticService.WARNING

        if reading.key == "rpm":
            numeric = cls._to_float(reading.value)
            if numeric is None:
                return "En attente", DiagnosticService.NORMAL
            if numeric < 900:
                return "Stable", DiagnosticService.NORMAL
            if numeric < 3000:
                return "Optimal", DiagnosticService.NORMAL
            if numeric <= 4000:
                return "Normal", DiagnosticService.NORMAL
            if numeric < 5000:
                return "A surveiller", DiagnosticService.WARNING
            return "Critique", DiagnosticService.CRITICAL

        if reading.key == "coolant_temp":
            numeric = cls._to_float(reading.value)
            if numeric is None:
                return "En attente", DiagnosticService.NORMAL
            if numeric < 70:
                return "Stable", DiagnosticService.NORMAL
            if numeric <= 98:
                return "Optimal", DiagnosticService.NORMAL
            if numeric <= 108:
                return "A surveiller", DiagnosticService.WARNING
            return "Critique", DiagnosticService.CRITICAL

        if reading.key == "hybrid_soc":
            numeric = cls._to_float(reading.value)
            if numeric is None:
                return "En attente", DiagnosticService.NORMAL
            if numeric < 35:
                return "A surveiller", DiagnosticService.WARNING
            if numeric < 55:
                return "Stable", DiagnosticService.NORMAL
            if numeric <= 80:
                return "Optimal", DiagnosticService.NORMAL
            return "Normal", DiagnosticService.NORMAL

        return "Disponible", DiagnosticService.NORMAL

    @staticmethod
    def _to_float(value) -> float | None:
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None
