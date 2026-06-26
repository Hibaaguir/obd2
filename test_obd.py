import logging

from app.core.obd_config import OBD_HOST, OBD_PORT
from app.services.obd_service import OBDDiagnosticReport, OBDService


def print_report(report: OBDDiagnosticReport):
    print("\n=== Diagnostic TCP/ELM327 ===")
    print(f"Cible: {report.host}:{report.port}")
    print("Formats verifies:")
    for candidate in report.candidates:
        print(f"  - {candidate}")

    print("\nCompatibilite des formats:")
    for check in report.format_checks:
        status = "OK" if check.compatible else "ECARTE"
        print(f"  [{status}] {check.value}")
        print(f"      Methode: {check.method}")
        print(f"      Detail: {check.detail}")

    print("\nEtapes:")
    for step in (
        report.network,
        report.socket,
        report.elm_handshake,
        report.python_obd,
    ):
        status = "OK" if step.success else "ECHEC"
        print(f"  [{status}] {step.name}: {step.detail}")

    print("\nTentatives python-obd:")
    for attempt in report.attempts:
        status = "OK" if attempt.success else "ECHEC"
        print(f"  [{status}] {attempt.method}")
        print(f"      URL: {attempt.url}")
        if attempt.status:
            print(f"      Status python-obd: {attempt.status}")
        if attempt.port_name:
            print(f"      Port python-obd: {attempt.port_name}")
        if attempt.protocol_id or attempt.protocol_name:
            print(f"      Protocole: {attempt.protocol_id} {attempt.protocol_name}".strip())
        if attempt.error:
            print(f"      Erreur: {attempt.error}")
        if attempt.traceback:
            print("      Traceback/details:")
            for line in attempt.traceback.splitlines():
                print(f"        {line}")

    print(f"\nPoint d'echec principal: {report.failure_stage}")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    service = OBDService()

    try:
        print("Tentative de connexion OBD2")
        print(f"Adresse IP utilisee: {OBD_HOST}")
        print(f"Port utilise: {OBD_PORT}")

        if not service.connect():
            print("Status: Non connecte")
            print(f"Connexion impossible: {service.last_error}")
            service.test_connection()

            print("\nLa connexion directe a echoue. Lancement du diagnostic detaille...")
            report = service.diagnose_connection()
            print_report(report)
            return

        connected = service.test_connection()
        print(f"Status: {'Connecte' if connected else 'Non connecte'}")

        readings = service.read_live_data(("rpm", "speed"))
        values = {reading.name: reading for reading in readings}

        rpm = values.get("RPM")
        speed = values.get("Vitesse")

        print(f"RPM: {rpm.value if rpm else 'Indisponible'} {rpm.unit if rpm else ''}".strip())
        print(f"SPEED: {speed.value if speed else 'Indisponible'} {speed.unit if speed else ''}".strip())

    except Exception as exc:
        print(f"Erreur OBD2: {exc.__class__.__name__}: {exc}")
        if service.last_error:
            print(f"Detail: {service.last_error}")
    finally:
        service.disconnect()


if __name__ == "__main__":
    main()
