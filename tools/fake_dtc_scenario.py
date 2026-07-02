from copy import deepcopy

from elm.obd_message import DT, ECU_ADDR_E, ECU_R_ADDR_E, ELM_FOOTER, HD, ObdMessage as BASE_OBD_MESSAGE, SZ


ObdMessage = {
    "car_fake_dtc": deepcopy(BASE_OBD_MESSAGE["car"]),
}

ObdMessage["car_fake_dtc"]["GET_DTC"] = {
    "Request": "^03" + ELM_FOOTER,
    "Descr": "Get DTCs (Diagnostic Trouble Codes) with fake test data",
    "Header": ECU_ADDR_E,
    "Response": HD(ECU_R_ADDR_E) + SZ("05") + DT("43 03 01 04 20"),
}
