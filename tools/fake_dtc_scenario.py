from copy import deepcopy

from elm.obd_message import DT, ECU_ADDR_E, ECU_R_ADDR_E, ELM_FOOTER, HD, ObdMessage as BASE_OBD_MESSAGE, SZ


def _fake_dtc_response(self, cmd, pid, uc_val):
    if self.counters.get("fake_dtc_cleared"):
        return HD(ECU_R_ADDR_E) + SZ("02") + DT("43 00")
    return HD(ECU_R_ADDR_E) + SZ("05") + DT("43 03 01 04 20")


ObdMessage = {
    "car_fake_dtc": deepcopy(BASE_OBD_MESSAGE["car"]),
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
