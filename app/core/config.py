from pathlib import Path


APP_NAME = "obd2"
APP_TITLE = "OBD2"
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "obd2.sqlite3"

PRIMARY_PALETTE = "Blue"
ACCENT_PALETTE = "Green"
