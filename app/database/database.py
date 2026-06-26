import json
import sqlite3
from contextlib import closing
from datetime import datetime
from typing import Any

from app.core.config import DATABASE_PATH, DATA_DIR
from app.services.obd_service import OBDTroubleCode


class Database:
    def __init__(self, database_path=DATABASE_PATH):
        self.database_path = database_path
        self._connection: sqlite3.Connection | None = None

    def initialize(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path)
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
        self.connection.commit()

    def save_measurement(self, data: dict[str, Any]):
        timestamp = data.get("timestamp") or datetime.now().isoformat(timespec="seconds")
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
        self.connection.executemany(
            """
            INSERT INTO dtc_codes(timestamp, code, description, severity)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        self.connection.commit()

    def get_measurements(self) -> list[sqlite3.Row]:
        cursor = self.connection.execute(
            """
            SELECT
                id,
                timestamp,
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
        }
        for name, column_type in columns.items():
            if name not in existing:
                cursor.execute(f"ALTER TABLE measurements ADD COLUMN {name} {column_type}")

    @staticmethod
    def _to_number(value: Any) -> float | None:
        if value in (None, "", "Indisponible"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
