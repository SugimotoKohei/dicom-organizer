"""Standalone entrypoint for dicom-organizer."""

import os
import sys
from dicom_organizer.gui import main


def _attach_windows_console() -> None:
    if os.name == "nt" and (sys.stdout is None or sys.stderr is None):
        try:
            import ctypes

            ATTACH_PARENT_PROCESS = -1
            if ctypes.windll.kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
                if sys.stdout is None:
                    sys.stdout = open("CONOUT$", "w", encoding="utf-8")
                if sys.stderr is None:
                    sys.stderr = open("CONOUT$", "w", encoding="utf-8")
        except Exception:
            pass


if __name__ == "__main__":
    _attach_windows_console()
    sys.exit(main(sys.argv[1:]))
