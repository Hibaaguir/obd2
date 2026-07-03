from dataclasses import dataclass
import json
import logging
import socket
import subprocess
import sys
import time
import traceback
from typing import Any, Iterable

import obd

from app.core.elm_pid_registry import ELM_EMULATOR_PIDS, PID_BY_KEY, ElmPid
from app.core.obd_config import OBD_BAUDRATE, OBD_HOST, OBD_PORT, OBD_TIMEOUT


logger = logging.getLogger(__name__)

PYTHON_OBD_PROBE_TIMEOUT = OBD_TIMEOUT + 5


@dataclass(frozen=True)
class OBDReading:
    name: str
    value: str
    unit: str = ""
    key: str = ""
    category: str = ""
    available: bool = True
    raw_response: str = ""


@dataclass(frozen=True)
class OBDTroubleCode:
    code: str
    description: str
    severity: str


@dataclass(frozen=True)
class ConnectionAttempt:
    method: str
    url: str
    success: bool
    status: str = ""
    port_name: str = ""
    protocol_id: str = ""
    protocol_name: str = ""
    error: str = ""
    traceback: str = ""


@dataclass(frozen=True)
class ConnectionFormatCheck:
    value: str
    method: str
    compatible: bool
    detail: str


@dataclass(frozen=True)
class DiagnosticStep:
    name: str
    success: bool
    detail: str


@dataclass(frozen=True)
class OBDDiagnosticReport:
    host: str
    port: int
    candidates: tuple[str, ...]
    format_checks: tuple[ConnectionFormatCheck, ...]
    network: DiagnosticStep
    socket: DiagnosticStep
    elm_handshake: DiagnosticStep
    python_obd: DiagnosticStep
    attempts: tuple[ConnectionAttempt, ...]

    @property
    def failure_stage(self) -> str:
        for step in (self.network, self.socket, self.elm_handshake, self.python_obd):
            if not step.success:
                return step.name
        return "aucun"


class OBDService:
    """ELM327 TCP service tailored for ELM327-emulator.

    Live data is read through raw ELM commands so the app can query both
    standard OBD-II PIDs and Toyota custom PIDs exposed by the emulator.
    The diagnostic helpers still keep python-OBD probes for compatibility
    checks, but dashboard readings are never fabricated.
    """

    LIVE_COMMANDS = PID_BY_KEY

    DTC_DESCRIPTIONS = {
        "P0100": "Circuit de debit d'air massique ou volumique",
        "P0115": "Circuit de temperature du liquide de refroidissement",
        "P0120": "Circuit capteur position papillon",
        "P0171": "Melange trop pauvre banc 1",
        "P0172": "Melange trop riche banc 1",
        "P0300": "Rates d'allumage aleatoires detectes",
        "P0301": "Rates d'allumage cylindre 1",
        "P0302": "Rates d'allumage cylindre 2",
        "P0303": "Rates d'allumage cylindre 3",
        "P0304": "Rates d'allumage cylindre 4",
        "P0420": "Efficacite catalyseur sous le seuil banc 1",
        "P0442": "Petite fuite detectee systeme EVAP",
        "P0500": "Capteur vitesse vehicule",
        "P0562": "Tension systeme basse",
        "P0563": "Tension systeme haute",
    }

    def __init__(self):
        self._connection: socket.socket | None = None
        self.last_error = ""
        self.current_host = OBD_HOST
        self.current_port = OBD_PORT
        self.current_url = ""
        self.current_method = ""
        self.last_attempts: list[ConnectionAttempt] = []
        self._current_header = ""

    def is_connected(self) -> bool:
        return self._connection is not None

    @property
    def status_label(self) -> str:
        if self.is_connected():
            return "Connecte"
        if self.last_error:
            return f"Erreur: {self.last_error}"
        return "Non connecte"

    def connect(self, host: str | None = None, port: int | str | None = None) -> bool:
        self.last_error = ""
        selected_host = self._resolve_host(host)
        port_for_logs = self._format_port_for_logs(port)

        logger.info("Tentative de connexion OBD2")
        logger.info("Adresse IP utilisee: %s", selected_host)
        logger.info("Port TCP utilise: %s", port_for_logs)
        logger.info("Baudrate force pour python-obd: %s", OBD_BAUDRATE)
        logger.info("Timeout: %s seconde(s)", OBD_TIMEOUT)

        try:
            selected_port = self._resolve_port(port)
            self.disconnect()
            self.current_host = selected_host
            self.current_port = selected_port
            self.last_attempts = []
            sock = socket.create_connection(
                (selected_host, selected_port),
                timeout=OBD_TIMEOUT,
            )
            sock.settimeout(OBD_TIMEOUT)
            self._connection = sock
            self.current_url = self._build_raw_tcp_url(selected_host, selected_port)
            self.current_method = "raw ELM327 TCP"
            self._initialize_elm_session()
            logger.info(
                "Connexion OBD2 reussie | methode=%s | cible=%s",
                self.current_method,
                self.current_url,
            )
            return True
        except Exception as exc:
            self.disconnect()
            self.last_error = self._format_connection_error(
                exc,
                selected_host,
                port_for_logs,
            )
            logger.exception(
                "Echec de connexion OBD2 sur %s:%s",
                selected_host,
                port_for_logs,
            )
            return False

    def disconnect(self):
        if self._connection:
            logger.info(
                "Deconnexion OBD2 de %s:%s | url=%s | methode=%s",
                self.current_host,
                self.current_port,
                self.current_url or "n/a",
                self.current_method or "n/a",
            )
            try:
                self._connection.close()
            except OSError:
                pass
        self._connection = None
        self._current_header = ""

    def test_connection(self) -> bool:
        connected = self.is_connected()
        status = "connecte" if connected else "non connecte"
        message = (
            f"Statut OBD2: {status} | "
            f"adresse IP: {self.current_host} | port: {self.current_port}"
        )
        if self.last_error:
            message = f"{message} | derniere erreur: {self.last_error}"
        logger.info(message)
        print(message)
        return connected

    def diagnose_connection(
        self,
        host: str | None = None,
        port: int | str | None = None,
        include_python_obd: bool = True,
    ) -> OBDDiagnosticReport:
        selected_host = self._resolve_host(host)
        selected_port = self._resolve_port(port)
        candidates = tuple(self._connection_candidates(selected_host, selected_port))
        format_checks = tuple(self._check_connection_formats(selected_host, selected_port))
        python_obd_candidates = tuple(
            check.value for check in format_checks if check.compatible
        )

        logger.info("Diagnostic OBD TCP demarre")
        logger.info("Adresse IP diagnostiquee: %s", selected_host)
        logger.info("Port TCP diagnostique: %s", selected_port)
        logger.info("Formats candidats: %s", ", ".join(candidates))
        for check in format_checks:
            logger.info(
                "Format connexion | valeur=%s | methode=%s | compatible=%s | detail=%s",
                check.value,
                check.method,
                check.compatible,
                check.detail,
            )

        network, socket_step, elm_step = self._diagnose_raw_socket_and_elm(
            selected_host,
            selected_port,
        )

        attempts: tuple[ConnectionAttempt, ...] = ()
        if include_python_obd:
            time.sleep(0.5)
            original_connection = self._connection
            self._connection = None
            attempt_list = [
                self._probe_python_obd_connection(url) for url in python_obd_candidates
            ]
            if self._connection:
                self._connection.close()
                self._connection = None
            self._connection = original_connection
            attempts = tuple(attempt_list)
            python_obd_step = self._build_python_obd_step(attempts)
        else:
            python_obd_step = DiagnosticStep(
                "python-obd",
                False,
                "non execute",
            )

        report = OBDDiagnosticReport(
            host=selected_host,
            port=selected_port,
            candidates=candidates,
            format_checks=format_checks,
            network=network,
            socket=socket_step,
            elm_handshake=elm_step,
            python_obd=python_obd_step,
            attempts=attempts,
        )
        logger.info("Diagnostic OBD TCP termine | echec=%s", report.failure_stage)
        return report

    def read_live_data(self, command_keys: Iterable[str] | None = None) -> list[OBDReading]:
        self._require_connection()
        readings: list[OBDReading] = []
        selected_commands = self._selected_live_commands(command_keys)
        try:
            for _, pid in selected_commands:
                readings.append(self._query_pid(pid))
        except Exception as exc:
            self.last_error = str(exc)
            raise RuntimeError(f"Erreur lecture donnees OBD2: {exc}") from exc
        return readings

    def read_error_codes(self) -> list[OBDTroubleCode]:
        self._require_connection()
        try:
            self._set_header("7E0")
            raw = self._send_command("03")
            if self._is_no_data(raw):
                return []
            return self._parse_dtc_response(raw)
        except Exception as exc:
            self.last_error = str(exc)
            raise RuntimeError(f"Erreur lecture codes defaut OBD2: {exc}") from exc

    def clear_error_codes(self) -> bool:
        self._require_connection()
        try:
            self._set_header("7E0")
            raw = self._send_command("04")
            return not self._is_no_data(raw)
        except Exception as exc:
            self.last_error = str(exc)
            raise RuntimeError(f"Erreur effacement codes defaut OBD2: {exc}") from exc

    def _initialize_elm_session(self):
        for command in ("ATZ", "ATE0", "ATL0", "ATS1", "ATH1", "ATSP6"):
            raw = self._send_command(command, delay=1.0 if command == "ATZ" else 0.2)
            logger.info("Init ELM | %s => %s", command, self._format_bytes(raw))
        self._current_header = ""

    def _query_pid(self, pid: ElmPid) -> OBDReading:
        raw_header = self._set_header(pid.header)
        if raw_header is not None and b"OK" not in raw_header.upper():
            return self._unavailable_reading(pid, raw_header)

        raw = self._send_command(pid.command)
        if self._is_no_data(raw):
            return self._unavailable_reading(pid, raw)

        payload = self._find_payload_for_pid(raw, pid)
        if payload is None:
            return self._unavailable_reading(pid, raw)

        try:
            decoded = pid.decoder(payload)
        except Exception as exc:
            logger.exception("Decodage impossible | pid=%s | raw=%s", pid.key, raw)
            return OBDReading(
                name=pid.label,
                value="Indisponible",
                unit=pid.unit,
                key=pid.key,
                category=pid.category,
                available=False,
                raw_response=f"decode error: {exc}; {self._format_bytes(raw)}",
            )

        return OBDReading(
            name=pid.label,
            value=self._format_decoded_value(decoded, pid.precision),
            unit=pid.unit,
            key=pid.key,
            category=pid.category,
            available=True,
            raw_response=self._format_bytes(raw),
        )

    def _set_header(self, header: str) -> bytes | None:
        if not header or header == self._current_header:
            return None
        raw_header = self._send_command(f"ATSH{header}")
        if b"OK" in raw_header.upper():
            self._current_header = header
        return raw_header

    def _send_command(self, command: str, delay: float = 0.2) -> bytes:
        self._require_connection()
        assert self._connection is not None
        payload = command.strip().encode("ascii") + b"\r"
        self._connection.sendall(payload)
        if delay:
            time.sleep(delay)
        return self._read_until_prompt()

    def _read_until_prompt(self) -> bytes:
        assert self._connection is not None
        chunks: list[bytes] = []
        while True:
            chunk = self._connection.recv(4096)
            if not chunk:
                raise ConnectionError("Connexion ELM327 fermee")
            chunks.append(chunk)
            if b">" in chunk:
                break
        return b"".join(chunks)

    def _find_payload_for_pid(self, raw: bytes, pid: ElmPid) -> list[int] | None:
        for payload in self._extract_payloads(raw):
            start = self._find_prefix(payload, pid.response_prefix)
            if start is None:
                continue
            return payload[start + len(pid.response_prefix):]
        return None

    @classmethod
    def _extract_payloads(cls, raw: bytes) -> list[list[int]]:
        text = raw.decode("ascii", "ignore").replace(">", "")
        lines = [
            line.strip()
            for line in text.replace("\r", "\n").split("\n")
            if line.strip()
        ]
        grouped: dict[str, list[int]] = {}
        standalone: list[list[int]] = []
        for line in lines:
            upper = line.upper()
            if upper in {"OK", "?", "NO DATA", "SEARCHING..."}:
                continue
            tokens = [token for token in upper.split() if cls._is_hex_token(token)]
            if len(tokens) < 2:
                continue

            header = ""
            if len(tokens[0]) == 3:
                header = tokens.pop(0)

            if not tokens:
                continue

            frame_type = int(tokens[0], 16)
            if 0x10 <= frame_type <= 0x1F and len(tokens) >= 3:
                data_tokens = tokens[2:]
            elif 0x20 <= frame_type <= 0x2F and len(tokens) >= 2:
                data_tokens = tokens[1:]
            elif len(tokens) >= 2 and int(tokens[0], 16) == len(tokens) - 1:
                data_tokens = tokens[1:]
            else:
                data_tokens = tokens

            data = [int(token, 16) for token in data_tokens]
            if header:
                grouped.setdefault(header, []).extend(data)
            else:
                standalone.append(data)

        return list(grouped.values()) + standalone

    @staticmethod
    def _find_prefix(payload: list[int], prefix: tuple[int, ...]) -> int | None:
        if not prefix:
            return 0
        prefix_len = len(prefix)
        for index in range(0, len(payload) - prefix_len + 1):
            if tuple(payload[index:index + prefix_len]) == prefix:
                return index
        return None

    @staticmethod
    def _is_hex_token(value: str) -> bool:
        if not value or len(value) > 3:
            return False
        try:
            int(value, 16)
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_no_data(raw: bytes) -> bool:
        upper = raw.upper()
        return b"NO DATA" in upper or b"?" in upper or not raw.strip()

    @staticmethod
    def _format_decoded_value(value: float | str, precision: int) -> str:
        if isinstance(value, str):
            return value or "Indisponible"
        if precision <= 0:
            return str(int(round(value)))
        return f"{value:.{precision}f}"

    def _unavailable_reading(self, pid: ElmPid, raw: bytes) -> OBDReading:
        return OBDReading(
            name=pid.label,
            value="Indisponible",
            unit=pid.unit,
            key=pid.key,
            category=pid.category,
            available=False,
            raw_response=self._format_bytes(raw),
        )

    def _parse_dtc_response(self, raw: bytes) -> list[OBDTroubleCode]:
        codes: list[OBDTroubleCode] = []
        for payload in self._extract_payloads(raw):
            start = self._find_prefix(payload, (0x43,))
            if start is None:
                continue
            data = payload[start + 1:]
            for index in range(0, len(data) - 1, 2):
                first = data[index]
                second = data[index + 1]
                if first == 0 and second == 0:
                    continue
                code = self._decode_dtc_pair(first, second)
                codes.append(self._build_dtc(code))
        return codes

    @staticmethod
    def _decode_dtc_pair(first: int, second: int) -> str:
        families = ("P", "C", "B", "U")
        family = families[(first & 0xC0) >> 6]
        digit_1 = (first & 0x30) >> 4
        digit_2 = first & 0x0F
        return f"{family}{digit_1:X}{digit_2:X}{second:02X}"

    def _require_connection(self):
        if not self.is_connected():
            self.last_error = "aucun adaptateur ELM327 connecte"
            raise ConnectionError("Aucun adaptateur ELM327 connecte")

    @staticmethod
    def _resolve_host(host: str | None) -> str:
        requested_host = host.strip() if host else ""
        return requested_host or OBD_HOST

    @staticmethod
    def _resolve_port(port: int | str | None) -> int:
        if port is None:
            return OBD_PORT
        if isinstance(port, int):
            return port

        requested_port = port.strip()
        if not requested_port:
            return OBD_PORT

        try:
            return int(requested_port)
        except ValueError as exc:
            raise ValueError(f"Port TCP invalide: {requested_port}") from exc

    @staticmethod
    def _build_tcp_url(host: str, port: int) -> str:
        return f"socket://{host}:{port}"

    @staticmethod
    def _build_raw_tcp_url(host: str, port: int) -> str:
        return f"{host}:{port}"

    @classmethod
    def _connection_candidates(cls, host: str, port: int) -> list[str]:
        alternate_host = "localhost" if host == "127.0.0.1" else "127.0.0.1"
        return [
            cls._build_tcp_url(host, port),
            cls._build_tcp_url(alternate_host, port),
            cls._build_raw_tcp_url(host, port),
            cls._build_raw_tcp_url(alternate_host, port),
        ]

    @classmethod
    def _python_obd_candidates(cls, host: str, port: int) -> list[str]:
        alternate_host = "localhost" if host == "127.0.0.1" else "127.0.0.1"
        return [
            cls._build_tcp_url(host, port),
            cls._build_tcp_url(alternate_host, port),
        ]

    @classmethod
    def _check_connection_formats(cls, host: str, port: int) -> list[ConnectionFormatCheck]:
        checks = []
        for value in cls._connection_candidates(host, port):
            if value.startswith("socket://"):
                checks.append(
                    ConnectionFormatCheck(
                        value=value,
                        method="pySerial serial_for_url TCP socket",
                        compatible=True,
                        detail=(
                            "format TCP valide pour python-obd 0.7.2 via pySerial; "
                            f"baudrate force a {OBD_BAUDRATE} pour eviter l'auto-baud"
                        ),
                    )
                )
            else:
                checks.append(
                    ConnectionFormatCheck(
                        value=value,
                        method="nom de port serie brut",
                        compatible=False,
                        detail=(
                            "pas un URL handler pySerial TCP; python-obd le traite "
                            "comme un nom de port serie local"
                        ),
                    )
                )
        return checks

    def _probe_python_obd_connection(self, url: str) -> ConnectionAttempt:
        method = "python-obd probe subprocess via pySerial serial_for_url"
        logger.info(
            "Probe python-obd | methode=%s | url=%s | timeout=%ss",
            method,
            url,
            PYTHON_OBD_PROBE_TIMEOUT,
        )

        code = (
            "import json, sys, traceback\n"
            "import obd\n"
            "url = sys.argv[1]\n"
            "timeout = float(sys.argv[2])\n"
            "baudrate = int(sys.argv[3])\n"
            "try:\n"
            "    connection = obd.OBD(portstr=url, baudrate=baudrate, fast=False, timeout=timeout, check_voltage=False)\n"
            "    result = {\n"
            "        'success': bool(connection.is_connected()),\n"
            "        'status': str(connection.status()),\n"
            "        'port_name': connection.port_name(),\n"
            "        'protocol_id': connection.protocol_id(),\n"
            "        'protocol_name': connection.protocol_name(),\n"
            "        'error': '' if connection.is_connected() else 'python-obd ouvert, mais statut non connecte au vehicule',\n"
            "        'traceback': '',\n"
            "    }\n"
            "    connection.close()\n"
            "except Exception as exc:\n"
            "    result = {\n"
            "        'success': False,\n"
            "        'status': '',\n"
            "        'port_name': '',\n"
            "        'protocol_id': '',\n"
            "        'protocol_name': '',\n"
            "        'error': f'{exc.__class__.__name__}: {exc}',\n"
            "        'traceback': traceback.format_exc(),\n"
            "    }\n"
            "print(json.dumps(result))\n"
        )

        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    code,
                    url,
                    str(OBD_TIMEOUT),
                    str(OBD_BAUDRATE),
                ],
                capture_output=True,
                text=True,
                timeout=PYTHON_OBD_PROBE_TIMEOUT,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            error = (
                f"TimeoutExpired: python-obd bloque plus de "
                f"{PYTHON_OBD_PROBE_TIMEOUT}s"
            )
            logger.error(
                "Timeout probe python-obd | url=%s | stdout=%s | stderr=%s",
                url,
                stdout,
                stderr,
            )
            return ConnectionAttempt(
                method=method,
                url=url,
                success=False,
                error=error,
                traceback=f"stdout:\n{stdout}\nstderr:\n{stderr}",
            )

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        logger.info(
            "Probe python-obd termine | url=%s | returncode=%s | stdout=%s | stderr=%s",
            url,
            completed.returncode,
            stdout,
            stderr,
        )

        result = self._parse_probe_result(stdout)
        if result is None:
            return ConnectionAttempt(
                method=method,
                url=url,
                success=False,
                error=(
                    f"probe python-obd sans JSON exploitable "
                    f"(returncode={completed.returncode})"
                ),
                traceback=f"stdout:\n{stdout}\nstderr:\n{stderr}",
            )

        error = str(result.get("error") or "")
        if completed.returncode != 0 and not error:
            error = f"probe python-obd termine avec returncode={completed.returncode}"

        return ConnectionAttempt(
            method=method,
            url=url,
            success=bool(result.get("success")),
            status=str(result.get("status") or ""),
            port_name=str(result.get("port_name") or ""),
            protocol_id=str(result.get("protocol_id") or ""),
            protocol_name=str(result.get("protocol_name") or ""),
            error=error,
            traceback=str(result.get("traceback") or stderr),
        )

    def _try_python_obd_connection(self, url: str) -> ConnectionAttempt:
        method = "python-obd via pySerial serial_for_url"
        logger.info("Tentative python-obd | methode=%s | url=%s", method, url)
        try:
            connection = obd.OBD(
                portstr=url,
                baudrate=OBD_BAUDRATE,
                fast=False,
                timeout=OBD_TIMEOUT,
                check_voltage=False,
            )
            status = str(connection.status())
            is_connected = connection.is_connected()
            port_name = connection.port_name()
            protocol_id = connection.protocol_id()
            protocol_name = connection.protocol_name()
            logger.info(
                "Reponse python-obd | url=%s | is_connected=%s | status=%s | "
                "port_name=%s | protocol_id=%s | protocol_name=%s",
                url,
                is_connected,
                status,
                port_name,
                protocol_id,
                protocol_name,
            )

            if is_connected:
                self._connection = connection
                return ConnectionAttempt(
                    method=method,
                    url=url,
                    success=True,
                    status=status,
                    port_name=port_name,
                    protocol_id=protocol_id,
                    protocol_name=protocol_name,
                )

            connection.close()
            return ConnectionAttempt(
                method=method,
                url=url,
                success=False,
                status=status,
                port_name=port_name,
                protocol_id=protocol_id,
                protocol_name=protocol_name,
                error="python-obd ouvert, mais statut non connecte au vehicule",
            )
        except Exception as exc:
            tb = traceback.format_exc()
            logger.exception(
                "Exception complete python-obd | methode=%s | url=%s",
                method,
                url,
            )
            return ConnectionAttempt(
                method=method,
                url=url,
                success=False,
                error=f"{exc.__class__.__name__}: {exc}",
                traceback=tb,
            )

    @staticmethod
    def _parse_probe_result(stdout: str) -> dict[str, Any] | None:
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        return None

    @staticmethod
    def _diagnose_network(host: str, port: int) -> DiagnosticStep:
        try:
            with socket.create_connection((host, port), timeout=2):
                return DiagnosticStep("reseau", True, f"TCP connect OK sur {host}:{port}")
        except OSError as exc:
            return DiagnosticStep("reseau", False, f"{exc.__class__.__name__}: {exc}")

    @classmethod
    def _diagnose_raw_socket_and_elm(
        cls,
        host: str,
        port: int,
    ) -> tuple[DiagnosticStep, DiagnosticStep, DiagnosticStep]:
        try:
            with socket.create_connection((host, port), timeout=2) as sock:
                sock.settimeout(2)
                network = DiagnosticStep("reseau", True, f"TCP connect OK sur {host}:{port}")

                ati = cls._send_raw_elm_command_on_socket(sock, b"ATI\r")
                if ati:
                    socket_step = DiagnosticStep("socket", True, cls._format_bytes(ati))
                else:
                    return (
                        network,
                        DiagnosticStep("socket", False, "aucune donnee recue apres ATI"),
                        DiagnosticStep("handshake ELM327", False, "ignore: socket muet"),
                    )

                atz = cls._send_raw_elm_command_on_socket(sock, b"ATZ\r", delay=1.0)
                ate0 = cls._send_raw_elm_command_on_socket(sock, b"ATE0\r")
                atl0 = cls._send_raw_elm_command_on_socket(sock, b"ATL0\r")
                raw = b" | ".join((ati, atz, ate0, atl0))
                text = cls._format_bytes(raw)
                ok = b">" in atz and (b"OK" in ate0.upper()) and (b"OK" in atl0.upper())
                elm_step = DiagnosticStep(
                    "handshake ELM327",
                    ok,
                    text if text else "reponse ELM incomplete",
                )
                return network, socket_step, elm_step
        except OSError as exc:
            network = DiagnosticStep("reseau", False, f"{exc.__class__.__name__}: {exc}")
            socket_step = DiagnosticStep("socket", False, "ignore: reseau inaccessible")
            elm_step = DiagnosticStep("handshake ELM327", False, "ignore: socket inaccessible")
            return network, socket_step, elm_step

    @classmethod
    def _diagnose_socket_response(cls, host: str, port: int) -> DiagnosticStep:
        try:
            response = cls._send_raw_elm_command(host, port, b"ATI\r")
            if response:
                return DiagnosticStep("socket", True, cls._format_bytes(response))
            return DiagnosticStep("socket", False, "aucune donnee recue apres ATI")
        except OSError as exc:
            return DiagnosticStep("socket", False, f"{exc.__class__.__name__}: {exc}")

    @classmethod
    def _diagnose_elm_handshake(cls, host: str, port: int) -> DiagnosticStep:
        try:
            atz = cls._send_raw_elm_command(host, port, b"ATZ\r", delay=1.0)
            ate0 = cls._send_raw_elm_command(host, port, b"ATE0\r")
            atl0 = cls._send_raw_elm_command(host, port, b"ATL0\r")
            raw = b" | ".join((atz, ate0, atl0))
            text = cls._format_bytes(raw)
            ok = b">" in atz and (b"OK" in ate0.upper()) and (b"OK" in atl0.upper())
            if ok:
                return DiagnosticStep("handshake ELM327", True, text)
            return DiagnosticStep("handshake ELM327", False, text or "reponse ELM incomplete")
        except OSError as exc:
            return DiagnosticStep("handshake ELM327", False, f"{exc.__class__.__name__}: {exc}")

    @staticmethod
    def _send_raw_elm_command(host: str, port: int, command: bytes, delay: float = 0.2) -> bytes:
        with socket.create_connection((host, port), timeout=2) as sock:
            sock.settimeout(2)
            sock.sendall(command)
            if delay:
                import time

                time.sleep(delay)

            chunks: list[bytes] = []
            while True:
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
                if b">" in chunk:
                    break
            return b"".join(chunks)

    @staticmethod
    def _send_raw_elm_command_on_socket(
        sock: socket.socket,
        command: bytes,
        delay: float = 0.2,
    ) -> bytes:
        sock.sendall(command)
        if delay:
            time.sleep(delay)

        chunks: list[bytes] = []
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)
            if b">" in chunk:
                break
        return b"".join(chunks)

    @staticmethod
    def _format_bytes(data: bytes) -> str:
        return data.decode("utf-8", "replace").replace("\r", "\\r").replace("\n", "\\n")

    @staticmethod
    def _build_python_obd_step(attempts: tuple[ConnectionAttempt, ...]) -> DiagnosticStep:
        successful = next((attempt for attempt in attempts if attempt.success), None)
        if successful:
            return DiagnosticStep(
                "python-obd",
                True,
                (
                    f"OK via {successful.url} | status={successful.status} | "
                    f"protocol={successful.protocol_id} {successful.protocol_name}"
                ),
            )

        details = []
        for attempt in attempts:
            reason = attempt.error or f"status={attempt.status}"
            details.append(f"{attempt.url} => {reason}")
        return DiagnosticStep("python-obd", False, " ; ".join(details))

    def _build_attempt_error(self) -> str:
        if not self.last_attempts:
            return "aucune tentative python-obd executee"

        details = []
        for attempt in self.last_attempts:
            reason = attempt.error or f"status={attempt.status}"
            details.append(f"{attempt.url} => {reason}")
        return "Echec python-obd: " + " ; ".join(details)

    @staticmethod
    def _format_port_for_logs(port: int | str | None) -> int | str:
        if port is None:
            return OBD_PORT
        if isinstance(port, int):
            return port
        return port.strip() or OBD_PORT

    @staticmethod
    def _format_connection_error(
        exc: Exception,
        host: str,
        port: int | str,
    ) -> str:
        target = f"{host}:{port}"
        if isinstance(exc, ConnectionRefusedError):
            hint = (
                "Demarrez l'emulateur avec `elm -s car -n 35000`."
                if host in {"127.0.0.1", "localhost"} and str(port) == str(OBD_PORT)
                else "Verifiez qu'un adaptateur ELM327 TCP/IP ecoute bien sur cette adresse."
            )
            return (
                f"Aucun service OBD2 n'ecoute sur {target}.\n"
                f"{hint}"
            )
        if isinstance(exc, TimeoutError):
            return (
                f"Le delai de connexion a expire vers {target}.\n"
                "Verifiez l'adresse IP, le port et la disponibilite de l'adaptateur."
            )
        if isinstance(exc, socket.gaierror):
            return (
                f"Adresse OBD2 invalide ou introuvable: {host}.\n"
                "Corrigez l'hote TCP/IP puis relancez la connexion."
            )
        if isinstance(exc, ValueError):
            return str(exc)
        return f"{exc.__class__.__name__}: {exc} (cible TCP {target})"

    @staticmethod
    def _format_response(value: Any) -> tuple[str, str]:
        magnitude = getattr(value, "magnitude", None)
        units = getattr(value, "units", "")
        if magnitude is None:
            return str(value), ""
        if isinstance(magnitude, float):
            display_value = f"{magnitude:.1f}"
        else:
            display_value = str(magnitude)
        return display_value, str(units)

    @classmethod
    def _selected_live_commands(
        cls,
        command_keys: Iterable[str] | None,
    ) -> list[tuple[str, ElmPid]]:
        if command_keys is None:
            return [(pid.key, pid) for pid in ELM_EMULATOR_PIDS]

        commands = []
        for key in command_keys:
            if key not in cls.LIVE_COMMANDS:
                raise ValueError(f"Commande live OBD inconnue: {key}")
            commands.append((key, cls.LIVE_COMMANDS[key]))
        return commands

    @classmethod
    def _build_dtc(cls, item: Any) -> OBDTroubleCode:
        if isinstance(item, tuple) and len(item) >= 2:
            code = str(item[0])
            raw_description = str(item[1]).strip()
        else:
            code = str(item)
            raw_description = ""
        description = raw_description or cls.DTC_DESCRIPTIONS.get(code) or cls._generic_dtc_description(code)
        return OBDTroubleCode(code=code, description=description, severity=cls._dtc_severity(code))

    @classmethod
    def _generic_dtc_description(cls, code: str) -> str:
        family = code[:1].upper()
        if family == "P":
            return "Defaut groupe motopropulseur"
        if family == "B":
            return "Defaut carrosserie ou habitacle"
        if family == "C":
            return "Defaut chassis"
        if family == "U":
            return "Defaut communication reseau"
        return "Description non fournie par l'ECU"

    @classmethod
    def _dtc_severity(cls, code: str) -> str:
        if code.startswith(("P03", "P056", "U0")):
            return "Elevee"
        if code.startswith(("P01", "P02", "P04", "C")):
            return "Moyenne"
        return "Faible"
 
