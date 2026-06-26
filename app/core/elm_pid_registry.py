from dataclasses import dataclass
from typing import Callable


Decoder = Callable[[list[int]], float | str]


@dataclass(frozen=True)
class ElmPid:
    key: str
    label: str
    command: str
    header: str
    response_prefix: tuple[int, ...]
    unit: str
    icon: str
    storage_field: str
    category: str
    decoder: Decoder
    precision: int = 1


def byte_a(data: list[int]) -> int:
    return data[0]


def bytes_ab(data: list[int]) -> int:
    return data[0] * 256 + data[1]


def speed(data: list[int]) -> float:
    return float(byte_a(data))


def rpm(data: list[int]) -> float:
    return bytes_ab(data) / 4


def temp_offset_40(data: list[int]) -> float:
    return byte_a(data) - 40


def percent(data: list[int]) -> float:
    return byte_a(data) * 100 / 255


def maf(data: list[int]) -> float:
    return bytes_ab(data) / 100


def voltage(data: list[int]) -> float:
    return bytes_ab(data) / 1000


def soc(data: list[int]) -> float:
    return byte_a(data) * 20 / 51


def signed_torque(data: list[int]) -> float:
    return bytes_ab(data) / 8 - 4096


def hybrid_current(data: list[int]) -> float:
    return bytes_ab(data) / 100 - 327.68


def odometer(data: list[int]) -> float:
    return data[0] * 256 * 256 + data[1] * 256 + data[2]


def fuel_liters(data: list[int]) -> float:
    return byte_a(data) / 2


def vin(data: list[int]) -> str:
    payload = data[1:] if data and data[0] == 0x01 else data
    return "".join(chr(value) for value in payload if 32 <= value <= 126).strip()


ELM_EMULATOR_PIDS: tuple[ElmPid, ...] = (
    ElmPid("rpm", "RPM", "010C", "7E0", (0x41, 0x0C), "rpm", "speedometer", "rpm", "Moteur", rpm, 0),
    ElmPid("speed", "Vitesse", "010D", "7E0", (0x41, 0x0D), "km/h", "car-speed-limiter", "speed", "Conduite", speed, 0),
    ElmPid("coolant_temp", "Temperature moteur", "0105", "7E0", (0x41, 0x05), "C", "thermometer", "coolant_temp", "Moteur", temp_offset_40, 0),
    ElmPid("engine_load", "Charge moteur", "0104", "7E0", (0x41, 0x04), "%", "engine-outline", "engine_load", "Moteur", percent, 1),
    ElmPid("intake_pressure", "Pression admission", "010B", "7E0", (0x41, 0x0B), "kPa", "gauge", "intake_pressure", "Moteur", speed, 0),
    ElmPid("intake_temp", "Temperature admission", "010F", "7E0", (0x41, 0x0F), "C", "thermometer-lines", "intake_temp", "Moteur", temp_offset_40, 0),
    ElmPid("maf", "Debit air MAF", "0110", "7E0", (0x41, 0x10), "g/s", "fan", "maf", "Moteur", maf, 2),
    ElmPid("throttle_pos", "Position papillon", "0111", "7E0", (0x41, 0x11), "%", "gauge", "throttle_pos", "Moteur", percent, 1),
    ElmPid("module_voltage", "Tension ECU", "0142", "7E0", (0x41, 0x42), "V", "car-battery", "battery_voltage", "Electrique", voltage, 2),
    ElmPid("ambient_temp", "Temperature ambiante", "0146", "7E0", (0x41, 0x46), "C", "weather-sunny", "ambient_temp", "Confort", temp_offset_40, 0),
    ElmPid("hybrid_soc", "Batterie hybride SOC", "015B", "7E2", (0x41, 0x5B), "%", "battery-high", "hybrid_soc", "Hybride", soc, 1),
    ElmPid("hybrid_current", "Courant batterie HV", "2198", "7E2", (0x61, 0x98), "A", "current-dc", "hybrid_battery_current", "Hybride", hybrid_current, 2),
    ElmPid("mg1_temp", "Temperature MG1", "2161", "7E2", (0x61, 0x61), "C", "thermometer", "mg1_temp", "Hybride", temp_offset_40, 0),
    ElmPid("mg2_temp", "Temperature MG2", "2162", "7E2", (0x61, 0x62), "C", "thermometer", "mg2_temp", "Hybride", temp_offset_40, 0),
    ElmPid("mg1_torque", "Couple MG1", "2167", "7E2", (0x61, 0x67), "Nm", "rotate-3d-variant", "mg1_torque", "Hybride", signed_torque, 1),
    ElmPid("mg2_torque", "Couple MG2", "2168", "7E2", (0x61, 0x68), "Nm", "rotate-3d-variant", "mg2_torque", "Hybride", signed_torque, 1),
    ElmPid("odometer", "Odometre", "2128", "7E2", (0x61, 0x28), "km", "counter", "odometer", "Vehicule", odometer, 0),
    ElmPid("fuel_level", "Carburant", "2129", "7C0", (0x61, 0x29), "L", "fuel", "fuel_level", "Vehicule", fuel_liters, 1),
    ElmPid("vin", "VIN", "0902", "7E0", (0x49, 0x02), "", "identifier", "vin", "Vehicule", vin, 0),
)


PID_BY_KEY = {pid.key: pid for pid in ELM_EMULATOR_PIDS}
