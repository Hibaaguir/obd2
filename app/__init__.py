"""OBD2 KivyMD application package."""

import os


# Disable Kivy file logging early so direct imports do not try to write
# under the user profile during local smoke checks.
os.environ.setdefault("KIVY_NO_FILELOG", "1")
