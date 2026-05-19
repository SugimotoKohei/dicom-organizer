"""Create a lightweight macOS app launcher for the GUI."""

from __future__ import annotations

import argparse
import plistlib
import shlex
import sys
from pathlib import Path

from dicom_organizer.core import __version__

APP_NAME = "dicom-organizer"
APP_IDENTIFIER = "io.github.SugimotoKohei.dicom-organizer"
EXECUTABLE_NAME = "dicom-organizer-gui"


def default_target_dir() -> Path:
    return Path.home() / "Applications"


def create_macos_app(
    target_dir: Path,
    *,
    name: str = APP_NAME,
    python_executable: Path | None = None,
    force: bool = False,
) -> Path:
    python_path = python_executable or Path(sys.executable)
    app_path = target_dir / f"{name}.app"
    contents_dir = app_path / "Contents"
    macos_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"
    executable_path = macos_dir / EXECUTABLE_NAME
    info_path = contents_dir / "Info.plist"

    if app_path.exists() and not force:
        msg = f"{app_path} already exists. Re-run with --force to replace launcher files."
        raise FileExistsError(msg)

    macos_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)

    plist = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleDisplayName": name,
        "CFBundleExecutable": EXECUTABLE_NAME,
        "CFBundleIdentifier": APP_IDENTIFIER,
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": name,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": __version__,
        "CFBundleVersion": __version__,
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
    }
    with info_path.open("wb") as handle:
        plistlib.dump(plist, handle)

    script = "\n".join(
        [
            "#!/bin/sh",
            'export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"',
            f"exec {shlex.quote(str(python_path))} -m dicom_organizer.gui \"$@\"",
            "",
        ]
    )
    executable_path.write_text(script, encoding="utf-8")
    executable_path.chmod(executable_path.stat().st_mode | 0o755)
    return app_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a lightweight macOS .app launcher for dicom-organizer-gui. "
            "The launcher uses the current Python environment, so keep this "
            "package installed after creating the app."
        )
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=default_target_dir(),
        help="Directory where the .app bundle is created. Default: ~/Applications.",
    )
    parser.add_argument("--name", default=APP_NAME, help="Application bundle name.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace launcher files if the .app bundle already exists.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if sys.platform != "darwin":
        print("dicom-organizer-gui-app is only supported on macOS.", file=sys.stderr)
        return 2
    try:
        app_path = create_macos_app(
            args.target_dir,
            name=args.name,
            python_executable=Path(sys.executable),
            force=args.force,
        )
    except FileExistsError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"Created {app_path}")
    print("Open it from Finder, Launchpad, or with:")
    print(f"open {shlex.quote(str(app_path))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
