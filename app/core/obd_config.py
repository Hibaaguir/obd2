"""Central OBD connection settings.

The current setup targets ELM327-emulator over TCP/IP:

    elm -s car -n 35000

When switching later to a real Bluetooth ELM327 adapter, keep the connection
details isolated here and in ``OBDService``.
"""

OBD_HOST = "127.0.0.1"
OBD_PORT = 35000
OBD_BAUDRATE = 38400
OBD_TIMEOUT = 10
