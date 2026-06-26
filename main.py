import os
import sys
import traceback
from pathlib import Path


os.environ.setdefault("KIVY_NO_FILELOG", "1")


def _workspace_crash_log() -> Path:
    return Path(__file__).resolve().parent / "data" / "crash.log"


def _log_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        return sys.__excepthook__(exc_type, exc_value, exc_traceback)

    log_path = _workspace_crash_log()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n=== Unhandled exception ===\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=handle)

    sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = _log_unhandled_exception


from app.core.app import OBD2App


if __name__ == "__main__":
    OBD2App().run()
