import json
import sqlite3
from threading import RLock
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any

from app.core.config import DATABASE_PATH, DATA_DIR
from app.services.obd_service import OBDTroubleCode


class Database:
    def __init__(self, database_path=DATABASE_PATH):
        self.database_path = database_path
        self._connection: sqlite3.Connection | None = None
        self._lock = RLock()

    def initialize(self):
        with self._lock:
            if self._connection is not None:
                return
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            with closing(self._connection.cursor()) as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS measurements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        rpm REAL,
                        speed REAL,
                        coolant_temp REAL,
                        battery_voltage REAL,
                        engine_load REAL,
                        intake_pressure REAL,
                        intake_temp REAL,
                        maf REAL,
                        throttle_pos REAL,
                        ambient_temp REAL,
                        hybrid_soc REAL,
                        hybrid_battery_current REAL,
                        mg1_temp REAL,
                        mg2_temp REAL,
                        mg1_torque REAL,
                        mg2_torque REAL,
                        odometer REAL,
                        fuel_level REAL,
                        vin TEXT,
                        raw_data TEXT
                    )
                    """
                )
                self._ensure_measurement_columns(cursor)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS dtc_codes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        code TEXT NOT NULL,
                        description TEXT,
                        severity TEXT
                    )
                    """
                )
            self._connection.commit()

    def save_measurement(self, data: dict[str, Any]):
        timestamp = data.get("timestamp") or datetime.now().isoformat(timespec="seconds")
        with self._lock:
            self.connection.execute(
                """
                INSERT INTO measurements(
                    timestamp,
                    rpm,
                    speed,
                    coolant_temp,
                    battery_voltage,
                    engine_load,
                    intake_pressure,
                    intake_temp,
                    maf,
                    throttle_pos,
                    ambient_temp,
                    hybrid_soc,
                    hybrid_battery_current,
                    mg1_temp,
                    mg2_temp,
                    mg1_torque,
                    mg2_torque,
                    odometer,
                    fuel_level,
                    vin,
                    raw_data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    self._to_number(data.get("rpm")),
                    self._to_number(data.get("speed")),
                    self._to_number(data.get("coolant_temp")),
                    self._to_number(data.get("battery_voltage")),
                    self._to_number(data.get("engine_load")),
                    self._to_number(data.get("intake_pressure")),
                    self._to_number(data.get("intake_temp")),
                    self._to_number(data.get("maf")),
                    self._to_number(data.get("throttle_pos")),
                    self._to_number(data.get("ambient_temp")),
                    self._to_number(data.get("hybrid_soc")),
                    self._to_number(data.get("hybrid_battery_current")),
                    self._to_number(data.get("mg1_temp")),
                    self._to_number(data.get("mg2_temp")),
                    self._to_number(data.get("mg1_torque")),
                    self._to_number(data.get("mg2_torque")),
                    self._to_number(data.get("odometer")),
                    self._to_number(data.get("fuel_level")),
                    data.get("vin"),
                    json.dumps(data.get("raw_data") or {}, ensure_ascii=True),
                ),
            )
            self.connection.commit()

    def save_history_snapshot(
        self,
        data: dict[str, Any],
        diagnostic_status: str,
        main_issue: str,
        diagnostic_summary: str,
        dtc_codes: list[OBDTroubleCode] | list[dict[str, Any]] | None = None,
    ) -> bool:
        timestamp = data.get("timestamp") or datetime.now().isoformat(timespec="seconds")
        dtc_codes = dtc_codes or []
        dtc_signature = self._dtc_signature(dtc_codes)
        dtc_count = len([item for item in dtc_signature.split("|") if item]) if dtc_signature else 0
        dtc_codes_text = self._dtc_codes_text(dtc_codes)

        with self._lock:
            if not self._should_save_history(timestamp, diagnostic_status, main_issue, dtc_signature):
                return False

            payload = dict(data)
            payload["timestamp"] = timestamp
            payload["diagnostic_status"] = diagnostic_status
            payload["main_issue"] = main_issue
            payload["diagnostic_summary"] = main_issue
            payload["history_summary"] = diagnostic_summary
            payload["dtc_count"] = dtc_count
            payload["dtc_codes"] = dtc_codes_text
            payload["dtc_signature"] = dtc_signature
            self._insert_measurement(payload)

            if dtc_codes:
                self._insert_dtc_codes(dtc_codes, timestamp)

            self.connection.commit()
            return True

    def save_dtc_codes(self, codes: list[OBDTroubleCode] | list[dict[str, Any]]):
        if not codes:
            return
        timestamp = datetime.now().isoformat(timespec="seconds")
        rows = []
        for code in codes:
            if isinstance(code, OBDTroubleCode):
                rows.append((timestamp, code.code, code.description, code.severity))
            else:
                rows.append(
                    (
                        code.get("timestamp") or timestamp,
                        code.get("code", ""),
                        code.get("description", ""),
                        code.get("severity", ""),
                    )
                )
        with self._lock:
            self.connection.executemany(
                """
                INSERT INTO dtc_codes(timestamp, code, description, severity)
                VALUES (?, ?, ?, ?)
                """,
                rows,
            )
            self.connection.commit()

    def get_measurements(self) -> list[sqlite3.Row]:
        with self._lock:
            cursor = self.connection.execute(
                """
                SELECT
                    id,
                    timestamp,
                    diagnostic_status,
                    main_issue,
                    diagnostic_summary,
                    history_summary,
                    dtc_count,
                    dtc_codes,
                    dtc_signature,
                    rpm,
                    speed,
                    coolant_temp,
                    battery_voltage,
                    engine_load,
                    hybrid_soc,
                    hybrid_battery_current,
                    mg1_temp,
                    mg2_temp,
                    mg1_torque,
                    mg2_torque,
                    odometer,
                    fuel_level,
                    vin
                FROM measurements
                ORDER BY timestamp DESC, id DESC
                """
            )
            return cursor.fetchall()

    def get_dtc_history(self) -> list[sqlite3.Row]:
        with self._lock:
            cursor = self.connection.execute(
                """
                SELECT id, timestamp, code, description, severity
                FROM dtc_codes
                ORDER BY timestamp DESC, id DESC
                """
            )
            return cursor.fetchall()

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self.initialize()
        return self._connection

    def close(self):
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    @staticmethod
    def _ensure_measurement_columns(cursor: sqlite3.Cursor):
        cursor.execute("PRAGMA table_info(measurements)")
        existing = {row[1] for row in cursor.fetchall()}
        columns = {
            "intake_pressure": "REAL",
            "intake_temp": "REAL",
            "maf": "REAL",
            "throttle_pos": "REAL",
            "ambient_temp": "REAL",
            "hybrid_soc": "REAL",
            "hybrid_battery_current": "REAL",
            "mg1_temp": "REAL",
            "mg2_temp": "REAL",
            "mg1_torque": "REAL",
            "mg2_torque": "REAL",
            "odometer": "REAL",
            "fuel_level": "REAL",
            "vin": "TEXT",
            "raw_data": "TEXT",
            "diagnostic_status": "TEXT",
            "main_issue": "TEXT",
            "diagnostic_summary": "TEXT",
            "history_summary": "TEXT",
            "dtc_count": "INTEGER",
            "dtc_codes": "TEXT",
            "dtc_signature": "TEXT",
        }
        for name, column_type in columns.items():
            if name not in existing:
                cursor.execute(f"ALTER TABLE measurements ADD COLUMN {name} {column_type}")

    def _insert_measurement(self, data: dict[str, Any]):
        self.connection.execute(
            """
            INSERT INTO measurements(
                timestamp,
                diagnostic_status,
                main_issue,
                diagnostic_summary,
                history_summary,
                dtc_count,
                dtc_codes,
                dtc_signature,
                rpm,
                speed,
                coolant_temp,
                battery_voltage,
                engine_load,
                intake_pressure,
                intake_temp,
                maf,
                throttle_pos,
                ambient_temp,
                hybrid_soc,
                hybrid_battery_current,
                mg1_temp,
                mg2_temp,
                mg1_torque,
                mg2_torque,
                odometer,
                fuel_level,
                vin,
                raw_data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["timestamp"],
                data.get("diagnostic_status", ""),
                data.get("main_issue", ""),
                data.get("diagnostic_summary", ""),
                data.get("history_summary", ""),
                data.get("dtc_count", 0),
                data.get("dtc_codes", ""),
                data.get("dtc_signature", ""),
                self._to_number(data.get("rpm")),
                self._to_number(data.get("speed")),
                self._to_number(data.get("coolant_temp")),
                self._to_number(data.get("battery_voltage")),
                self._to_number(data.get("engine_load")),
                self._to_number(data.get("intake_pressure")),
                self._to_number(data.get("intake_temp")),
                self._to_number(data.get("maf")),
                self._to_number(data.get("throttle_pos")),
                self._to_number(data.get("ambient_temp")),
                self._to_number(data.get("hybrid_soc")),
                self._to_number(data.get("hybrid_battery_current")),
                self._to_number(data.get("mg1_temp")),
                self._to_number(data.get("mg2_temp")),
                self._to_number(data.get("mg1_torque")),
                self._to_number(data.get("mg2_torque")),
                self._to_number(data.get("odometer")),
                self._to_number(data.get("fuel_level")),
                data.get("vin"),
                json.dumps(data.get("raw_data") or {}, ensure_ascii=True),
            ),
        )

    def _insert_dtc_codes(self, codes: list[OBDTroubleCode] | list[dict[str, Any]], timestamp: str):
        rows = []
        for code in codes:
            if isinstance(code, OBDTroubleCode):
                rows.append((timestamp, code.code, code.description, code.severity))
            else:
                rows.append(
                    (
                        code.get("timestamp") or timestamp,
                        code.get("code", ""),
                        code.get("description", ""),
                        code.get("severity", ""),
                    )
                )
        self.connection.executemany(
            """
            INSERT INTO dtc_codes(timestamp, code, description, severity)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )

    def _should_save_history(self, timestamp: str, diagnostic_status: str, main_issue: str, dtc_signature: str) -> bool:
        cursor = self.connection.execute(
            """
            SELECT timestamp, diagnostic_status, main_issue, dtc_signature
            FROM measurements
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
            """
        )
        previous = cursor.fetchone()
        if previous is None:
            return True

        previous_time = self._parse_timestamp(previous["timestamp"])
        current_time = self._parse_timestamp(timestamp)
        if previous_time is None or current_time is None:
            return True

        if current_time - previous_time > timedelta(minutes=30):
            return True

        if (previous["diagnostic_status"] or "") != (diagnostic_status or ""):
            return True

        if (previous["main_issue"] or "") != (main_issue or ""):
            return True

        if (previous["dtc_signature"] or "") != (dtc_signature or ""):
            return True

        return False

    @staticmethod
    def _dtc_codes_text(codes: list[OBDTroubleCode] | list[dict[str, Any]]) -> str:
        if not codes:
            return ""

        normalized = []
        for code in codes:
            if isinstance(code, OBDTroubleCode):
                normalized.append(code.code.strip().upper())
            else:
                normalized.append(str(code.get("code", "")).strip().upper())
        return ", ".join(item for item in normalized if item)

    @staticmethod
    def _dtc_signature(codes: list[OBDTroubleCode] | list[dict[str, Any]]) -> str:
        if not codes:
            return ""

        normalized = []
        for code in codes:
            if isinstance(code, OBDTroubleCode):
                normalized.append(code.code.strip().upper())
            else:
                normalized.append(str(code.get("code", "")).strip().upper())
        return "|".join(sorted(item for item in normalized if item))

    @staticmethod
    def _parse_timestamp(value: str) -> datetime | None:
        text = str(value or "").strip()
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _to_number(value: Any) -> float | None:
        if value in (None, "", "Indisponible"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
