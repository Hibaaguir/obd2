from dataclasses import dataclass
from typing import Any

from app.core.elm_pid_registry import PID_BY_KEY
from app.services.obd_service import OBDReading, OBDTroubleCode


@dataclass(frozen=True)
class DiagnosticResult:
    title: str
    message: str
    severity: str


class DiagnosticService:
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    SEVERITY_RANK = {
        NORMAL: 0,
        WARNING: 1,
        CRITICAL: 2,
    }

    def analyze(
        self,
        live_data: list[OBDReading] | dict[str, Any] | None = None,
        dtc_codes: list[OBDTroubleCode] | list[dict[str, Any]] | None = None,
    ) -> list[DiagnosticResult]:
        data = self._normalize_live_data(live_data)
        codes = self._normalize_dtc_codes(dtc_codes or [])
        results: list[DiagnosticResult] = []

        battery_voltage = self._to_float(data.get("battery_voltage"))
        if battery_voltage is not None and battery_voltage < 12:
            results.append(
                DiagnosticResult(
                    title="Batterie faible",
                    message=f"Tension batterie mesuree a {battery_voltage:.1f} V.",
                    severity=self.WARNING,
                )
            )

        coolant_temp = self._to_float(data.get("coolant_temp"))
        if coolant_temp is not None and coolant_temp > 100:
            results.append(
                DiagnosticResult(
                    title="Temperature moteur elevee",
                    message=f"Temperature liquide moteur mesuree a {coolant_temp:.1f} deg C.",
                    severity=self.CRITICAL,
                )
            )

        rpm = self._to_float(data.get("rpm"))
        speed = self._to_float(data.get("speed"))
        engine_load = self._to_float(data.get("engine_load"))
        if rpm is not None and rpm > 4000:
            results.append(
                DiagnosticResult(
                    title="Regime moteur eleve",
                    message=f"Regime moteur mesure a {rpm:.0f} tr/min.",
                    severity=self.WARNING,
                )
            )
        elif (
            rpm is not None
            and speed is not None
            and engine_load is not None
            and speed <= 5
            and rpm >= 1000
            and engine_load >= 30
        ):
            results.append(
                DiagnosticResult(
                    title="Ralenti moteur irregulier",
                    message=f"Ralenti eleve a {rpm:.0f} tr/min avec charge moteur a {engine_load:.0f}%.",
                    severity=self.WARNING,
                )
            )

        hybrid_soc = self._to_float(data.get("hybrid_soc"))
        if hybrid_soc is not None and hybrid_soc < 35:
            results.append(
                DiagnosticResult(
                    title="Batterie hybride basse",
                    message=f"Etat de charge hybride mesure a {hybrid_soc:.1f}%.",
                    severity=self.WARNING,
                )
            )

        hv_current = self._to_float(data.get("hybrid_battery_current"))
        if hv_current is not None and abs(hv_current) > 150:
            results.append(
                DiagnosticResult(
                    title="Courant batterie HV eleve",
                    message=f"Courant batterie hybride mesure a {hv_current:.1f} A.",
                    severity=self.WARNING,
                )
            )

        for field, label in (("mg1_temp", "MG1"), ("mg2_temp", "MG2")):
            temp = self._to_float(data.get(field))
            if temp is not None and temp > 90:
                results.append(
                    DiagnosticResult(
                        title=f"Temperature {label} elevee",
                        message=f"Temperature {label} mesuree a {temp:.0f} deg C.",
                        severity=self.CRITICAL,
                    )
                )

        if codes:
            results.append(self._build_dtc_result(codes))

        if not results:
            return [
                DiagnosticResult(
                    title="Etat normal",
                    message="Aucune anomalie detectee avec les donnees disponibles.",
                    severity=self.NORMAL,
                )
            ]

        return self._sort_results(results)

    def overall_severity(self, results: list[DiagnosticResult]) -> str:
        severities = [result.severity for result in results]
        if self.CRITICAL in severities:
            return self.CRITICAL
        if self.WARNING in severities:
            return self.WARNING
        return self.NORMAL

    @classmethod
    def _normalize_live_data(cls, live_data: list[OBDReading] | dict[str, Any] | None) -> dict[str, Any]:
        if live_data is None:
            return {}
        if isinstance(live_data, dict):
            return live_data

        normalized: dict[str, Any] = {}
        for reading in live_data:
            pid = PID_BY_KEY.get(reading.key)
            if pid and reading.available:
                normalized[pid.storage_field] = reading.value
        return normalized

    @classmethod
    def _normalize_dtc_codes(
        cls,
        dtc_codes: list[OBDTroubleCode] | list[dict[str, Any]],
    ) -> list[OBDTroubleCode]:
        normalized: list[OBDTroubleCode] = []
        for code in dtc_codes:
            if isinstance(code, OBDTroubleCode):
                normalized.append(code)
                continue
            normalized.append(
                OBDTroubleCode(
                    code=str(code.get("code", "")).strip().upper(),
                    description=str(code.get("description", "")).strip(),
                    severity=str(code.get("severity", "")).strip(),
                )
            )
        return normalized

    @classmethod
    def _build_dtc_result(cls, codes: list[OBDTroubleCode]) -> DiagnosticResult:
        critical_count = sum(1 for code in codes if cls._normalize_severity(code.severity) == cls.CRITICAL)
        warning_count = sum(1 for code in codes if cls._normalize_severity(code.severity) == cls.WARNING)

        if critical_count:
            severity = cls.CRITICAL
            title = "Code DTC critique actif"
        elif warning_count:
            severity = cls.WARNING
            title = "Code DTC a surveiller"
        else:
            severity = cls.NORMAL
            title = "Code DTC memorise"

        details = [f"{len(codes)} code(s) DTC actif(s)"]
        if critical_count:
            details.append(f"{critical_count} critique(s)")
        if warning_count:
            details.append(f"{warning_count} a surveiller")

        return DiagnosticResult(
            title=title,
            message=", ".join(details) + ".",
            severity=severity,
        )

    @classmethod
    def _sort_results(cls, results: list[DiagnosticResult]) -> list[DiagnosticResult]:
        return sorted(results, key=lambda item: cls.SEVERITY_RANK.get(item.severity, -1), reverse=True)

    @classmethod
    def _normalize_severity(cls, severity: str) -> str:
        normalized = (severity or "").strip().lower()
        if normalized in {cls.CRITICAL, "critique", "elevee", "haute"}:
            return cls.CRITICAL
        if normalized in {cls.WARNING, "alerte", "moyenne"}:
            return cls.WARNING
        return cls.NORMAL

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value in (None, "", "Indisponible"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
