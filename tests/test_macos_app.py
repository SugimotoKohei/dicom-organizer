from __future__ import annotations

import os
import plistlib
from pathlib import Path

import pytest

from dicom_organizer.core import __version__
from dicom_organizer.macos_app import create_macos_app


def test_create_macos_app_writes_launcher_bundle(tmp_path: Path) -> None:
    app_path = create_macos_app(
        tmp_path,
        name="Test Organizer",
        python_executable=Path("/usr/bin/python3"),
    )

    info_path = app_path / "Contents" / "Info.plist"
    executable_path = app_path / "Contents" / "MacOS" / "dicom-organizer-gui"

    with info_path.open("rb") as handle:
        info = plistlib.load(handle)

    assert info["CFBundleName"] == "Test Organizer"
    assert info["CFBundleExecutable"] == "dicom-organizer-gui"
    assert info["CFBundleShortVersionString"] == __version__
    assert executable_path.read_text(encoding="utf-8").strip().endswith(
        '-m dicom_organizer.gui "$@"'
    )
    assert os.access(executable_path, os.X_OK)


def test_create_macos_app_refuses_existing_bundle_without_force(tmp_path: Path) -> None:
    create_macos_app(tmp_path, python_executable=Path("/usr/bin/python3"))

    with pytest.raises(FileExistsError, match="already exists"):
        create_macos_app(tmp_path, python_executable=Path("/usr/bin/python3"))

    app_path = create_macos_app(tmp_path, python_executable=Path("/usr/bin/python3"), force=True)
    assert app_path.exists()
