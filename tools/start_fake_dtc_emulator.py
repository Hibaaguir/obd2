import logging
import socket
import time

from elm import Elm

from fake_dtc_scenario import ObdMessage as FAKE_DTC_SCENARIOS


HOST = "127.0.0.1"
PORT = 35000
SCENARIO_NAME = "car_fake_dtc"


def ensure_port_available(host: str, port: int):
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
    except OSError as exc:
        raise RuntimeError(
            f"Le port TCP {host}:{port} est deja occupe. "
            "Fermez les anciens emulateurs avant d'en lancer un nouveau."
        ) from exc
    finally:
        probe.close()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    ensure_port_available(HOST, PORT)

    emulator = Elm(batch_mode=False, net_port=PORT)
    emulator.ObdMessage.update(FAKE_DTC_SCENARIOS)
    emulator.set_sorted_obd_msg(SCENARIO_NAME)

    try:
        with emulator as session:
            while session.threadState == session.THREAD.STARTING:
                time.sleep(0.1)
            if session.threadState == session.THREAD.TERMINATED:
                raise RuntimeError("The emulator could not start.")

            print(f"ELM327 emulator started on {HOST}:{PORT}")
            print(f"Scenario: {SCENARIO_NAME}")
            print("Fake DTCs enabled: P0301, P0420")
            print("Leave this window open while running the app. Press Ctrl+C to stop.\n")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping emulator...")


if __name__ == "__main__":
    main()
