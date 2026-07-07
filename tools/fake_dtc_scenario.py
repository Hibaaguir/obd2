from copy import deepcopy

from elm.obd_message import DT, ECU_ADDR_E, ECU_R_ADDR_E, ELM_FOOTER, HD, ObdMessage as BASE_OBD_MESSAGE, SZ


def _elm_response(size: str, data: str) -> str:
    return HD(ECU_R_ADDR_E) + SZ(size) + DT(data)


PROFILE_KEY = "fake_profile_index"
PROFILE_ADVANCE_KEY = "fake_profile_advance_pending"
CLEARED_KEY = "fake_dtc_cleared"


FAULT_PROFILES = (
    {
        "name": "idle_misfire",
        "dtcs": ("P0301", "P0420"),
        "rpm": ("04", "41 0C 12 C0"),  # 1200 rpm
        "speed": ("03", "41 0D 00"),
        "coolant_temp": ("03", "41 05 7E"),  # 86 C
        "engine_load": ("03", "41 04 61"),  # 38%
        "intake_pressure": ("03", "41 0B 2B"),
        "intake_temp": ("03", "41 0F 47"),
        "maf": ("04", "41 10 02 30"),
        "throttle_pos": ("03", "41 11 2E"),
        "module_voltage": ("04", "41 42 36 4C"),  # 13.9 V
    },
    {
        "name": "overheat_low_voltage",
        "dtcs": ("P0115", "P0562"),
        "rpm": ("04", "41 0C 0F A0"),  # 1000 rpm
        "speed": ("03", "41 0D 00"),
        "coolant_temp": ("03", "41 05 91"),  # 105 C
        "engine_load": ("03", "41 04 52"),  # 32%
        "intake_pressure": ("03", "41 0B 24"),
        "intake_temp": ("03", "41 0F 49"),
        "maf": ("04", "41 10 01 F4"),
        "throttle_pos": ("03", "41 11 24"),
        "module_voltage": ("04", "41 42 2D D0"),  # 11.7 V
    },
    {
        "name": "high_rev_lean_mix",
        "dtcs": ("P0300", "P0171"),
        "rpm": ("04", "41 0C 46 50"),  # 4500 rpm
        "speed": ("03", "41 0D 18"),  # 24 km/h
        "coolant_temp": ("03", "41 05 7C"),  # 84 C
        "engine_load": ("03", "41 04 8A"),  # 54%
        "intake_pressure": ("03", "41 0B 30"),
        "intake_temp": ("03", "41 0F 45"),
        "maf": ("04", "41 10 03 20"),
        "throttle_pos": ("03", "41 11 50"),
        "module_voltage": ("04", "41 42 36 B0"),  # 14.0 V
    },
    {
        "name": "evap_warning_only",
        "dtcs": ("P0442",),
        "rpm": ("04", "41 0C 0C E4"),  # 825 rpm
        "speed": ("03", "41 0D 00"),
        "coolant_temp": ("03", "41 05 7A"),  # 82 C
        "engine_load": ("03", "41 04 22"),  # 13%
        "intake_pressure": ("03", "41 0B 1C"),
        "intake_temp": ("03", "41 0F 44"),
        "maf": ("04", "41 10 01 18"),
        "throttle_pos": ("03", "41 11 18"),
        "module_voltage": ("04", "41 42 35 98"),  # 13.7 V
    },
)


NORMAL_PROFILE = {
    "rpm": ("04", "41 0C 0C 30"),
    "speed": ("03", "41 0D 00"),
    "coolant_temp": ("03", "41 05 7C"),
    "engine_load": ("03", "41 04 2E"),
    "intake_pressure": ("03", "41 0B 20"),
    "intake_temp": ("03", "41 0F 45"),
    "maf": ("04", "41 10 01 0E"),
    "throttle_pos": ("03", "41 11 1C"),
    "module_voltage": ("04", "41 42 37 14"),
}


def _current_profile(self):
    if self.counters.get(CLEARED_KEY):
        return NORMAL_PROFILE

    index = self.counters.get(PROFILE_KEY, 0) % len(FAULT_PROFILES)
    return FAULT_PROFILES[index]


def _advance_profile(self):
    current = self.counters.get(PROFILE_KEY, -1) + 1
    self.counters[PROFILE_KEY] = current % len(FAULT_PROFILES)
    self.counters[PROFILE_ADVANCE_KEY] = False


def _maybe_advance_profile(self):
    if self.counters.get(CLEARED_KEY):
        return
    if self.counters.get(PROFILE_ADVANCE_KEY, True):
        _advance_profile(self)


def _pid_response(profile_key: str, advance_profile: bool = False):
    def responder(self, cmd, pid, uc_val):
        if advance_profile:
            _maybe_advance_profile(self)

        profile = _current_profile(self)
        size, data = profile.get(profile_key, NORMAL_PROFILE[profile_key])
        return _elm_response(size, data)

    return responder


def _encode_dtc(code: str) -> tuple[int, int]:
    normalized = str(code or "").strip().upper()
    if len(normalized) != 5:
        raise ValueError(f"Code DTC invalide: {code}")

    family_bits = {
        "P": 0b00,
        "C": 0b01,
        "B": 0b10,
        "U": 0b11,
    }[normalized[0]]
    digit_1 = int(normalized[1], 16)
    digit_2 = int(normalized[2], 16)
    low_byte = int(normalized[3:], 16)
    high_byte = (family_bits << 6) | (digit_1 << 4) | digit_2
    return high_byte, low_byte


def _fake_dtc_response(self, cmd, pid, uc_val):
    profile = _current_profile(self)
    if self.counters.get(CLEARED_KEY):
        return _elm_response("02", "43 00")

    dtcs = profile.get("dtcs", ())
    bytes_out: list[int] = [0x43]
    for code in dtcs:
        high_byte, low_byte = _encode_dtc(code)
        bytes_out.extend((high_byte, low_byte))

    data = " ".join(f"{value:02X}" for value in bytes_out)
    size = f"{len(bytes_out):02X}"
    self.counters[PROFILE_ADVANCE_KEY] = True
    return _elm_response(size, data)


ObdMessage = {
    "car_fake_dtc": deepcopy(BASE_OBD_MESSAGE["car"]),
}


def _base_entry(name: str, response_footer, descr_suffix: str):
    base_entry = BASE_OBD_MESSAGE["car"][name]
    return {
        "Request": base_entry["Request"],
        "Descr": f"{base_entry['Descr']} ({descr_suffix})",
        "Header": base_entry["Header"],
        "ResponseFooter": response_footer,
    }


ObdMessage["car_fake_dtc"]["GET_DTC"] = {
    "Request": "^03" + ELM_FOOTER,
    "Descr": "Get rotating fake DTC test data",
    "Header": ECU_ADDR_E,
    "ResponseFooter": _fake_dtc_response,
}

ObdMessage["car_fake_dtc"]["CLEAR_DIAG_TC"] = {
    "Request": "^04" + ELM_FOOTER,
    "Descr": "Clear Diagnostic Trouble Codes and stored values",
    "Header": ECU_ADDR_E,
    "Exec": 'self.counters["fake_dtc_cleared"] = True',
    "Response": HD(ECU_R_ADDR_E) + SZ("01") + DT("44"),
}

ObdMessage["car_fake_dtc"]["RPM"] = _base_entry(
    "RPM",
    _pid_response("rpm", advance_profile=True),
    "rotating DTC profile",
)

ObdMessage["car_fake_dtc"]["SPEED"] = _base_entry(
    "SPEED",
    _pid_response("speed"),
    "rotating DTC profile",
)

ObdMessage["car_fake_dtc"]["COOLANT_TEMP"] = _base_entry(
    "COOLANT_TEMP",
    _pid_response("coolant_temp"),
    "rotating DTC profile",
)

ObdMessage["car_fake_dtc"]["ENGINE_LOAD"] = _base_entry(
    "ENGINE_LOAD",
    _pid_response("engine_load"),
    "rotating DTC profile",
)

ObdMessage["car_fake_dtc"]["INTAKE_PRESSURE"] = _base_entry(
    "INTAKE_PRESSURE",
    _pid_response("intake_pressure"),
    "rotating DTC profile",
)

ObdMessage["car_fake_dtc"]["INTAKE_TEMP"] = _base_entry(
    "INTAKE_TEMP",
    _pid_response("intake_temp"),
    "rotating DTC profile",
)

ObdMessage["car_fake_dtc"]["MAF"] = _base_entry(
    "MAF",
    _pid_response("maf"),
    "rotating DTC profile",
)

ObdMessage["car_fake_dtc"]["THROTTLE_POS"] = _base_entry(
    "THROTTLE_POS",
    _pid_response("throttle_pos"),
    "rotating DTC profile",
)

ObdMessage["car_fake_dtc"]["CONTROL_MODULE_VOLTAGE"] = _base_entry(
    "CONTROL_MODULE_VOLTAGE",
    _pid_response("module_voltage"),
    "rotating DTC profile",
)
