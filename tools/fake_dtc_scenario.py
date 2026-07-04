from copy import deepcopy

from elm.obd_message import DT, ECU_ADDR_E, ECU_R_ADDR_E, ELM_FOOTER, HD, ObdMessage as BASE_OBD_MESSAGE, SZ


def _elm_response(size: str, data: str) -> str:
    return HD(ECU_R_ADDR_E) + SZ(size) + DT(data)


def _cycling_response(counter_key: str, fault_packets: list[tuple[str, str]], normal_packet: tuple[str, str]):
    def responder(self, cmd, pid, uc_val):
        if self.counters.get("fake_dtc_cleared"):
            size, data = normal_packet
            return _elm_response(size, data)

        index = self.counters.get(counter_key, 0)
        self.counters[counter_key] = index + 1
        size, data = fault_packets[index % len(fault_packets)]
        return _elm_response(size, data)

    return responder


def _fake_dtc_response(self, cmd, pid, uc_val):
    if self.counters.get("fake_dtc_cleared"):
        return _elm_response("02", "43 00")
    return _elm_response("05", "43 03 01 04 20")


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
    "Descr": "Get DTCs (Diagnostic Trouble Codes) with fake test data",
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
    _cycling_response(
        "rpm_fault_cycle",
        [
            ("04", "41 0C 12 C0"),
            ("04", "41 0C 16 A8"),
            ("04", "41 0C 0F 50"),
        ],
        ("04", "41 0C 0C 30"),
    ),
    "DTC coherence profile",
)

ObdMessage["car_fake_dtc"]["SPEED"] = _base_entry(
    "SPEED",
    _cycling_response(
        "speed_fault_cycle",
        [("03", "41 0D 00")],
        ("03", "41 0D 00"),
    ),
    "DTC coherence profile",
)

ObdMessage["car_fake_dtc"]["COOLANT_TEMP"] = _base_entry(
    "COOLANT_TEMP",
    _cycling_response(
        "coolant_fault_cycle",
        [("03", "41 05 7E")],
        ("03", "41 05 7C"),
    ),
    "DTC coherence profile",
)

ObdMessage["car_fake_dtc"]["ENGINE_LOAD"] = _base_entry(
    "ENGINE_LOAD",
    _cycling_response(
        "engine_load_fault_cycle",
        [
            ("03", "41 04 61"),
            ("03", "41 04 70"),
            ("03", "41 04 66"),
        ],
        ("03", "41 04 2E"),
    ),
    "DTC coherence profile",
)

ObdMessage["car_fake_dtc"]["INTAKE_PRESSURE"] = _base_entry(
    "INTAKE_PRESSURE",
    _cycling_response(
        "intake_pressure_fault_cycle",
        [("03", "41 0B 2B")],
        ("03", "41 0B 20"),
    ),
    "DTC coherence profile",
)

ObdMessage["car_fake_dtc"]["INTAKE_TEMP"] = _base_entry(
    "INTAKE_TEMP",
    _cycling_response(
        "intake_temp_fault_cycle",
        [("03", "41 0F 47")],
        ("03", "41 0F 45"),
    ),
    "DTC coherence profile",
)

ObdMessage["car_fake_dtc"]["MAF"] = _base_entry(
    "MAF",
    _cycling_response(
        "maf_fault_cycle",
        [
            ("04", "41 10 02 30"),
            ("04", "41 10 02 80"),
        ],
        ("04", "41 10 01 0E"),
    ),
    "DTC coherence profile",
)

ObdMessage["car_fake_dtc"]["THROTTLE_POS"] = _base_entry(
    "THROTTLE_POS",
    _cycling_response(
        "throttle_fault_cycle",
        [
            ("03", "41 11 2E"),
            ("03", "41 11 36"),
        ],
        ("03", "41 11 1C"),
    ),
    "DTC coherence profile",
)

ObdMessage["car_fake_dtc"]["CONTROL_MODULE_VOLTAGE"] = _base_entry(
    "CONTROL_MODULE_VOLTAGE",
    _cycling_response(
        "voltage_fault_cycle",
        [("04", "41 42 36 4C")],
        ("04", "41 42 37 14"),
    ),
    "DTC coherence profile",
)
