#!/usr/bin/env python3
"""Build standalone distribution packages using PyInstaller."""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
from dicom_organizer import __version__ as APP_VERSION  # noqa: E402


def get_os_arch() -> tuple[str, str]:
    """Return normalized (os_name, arch) string pair."""
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        os_name = "macos"
        arch = "arm64" if machine in ("arm64", "aarch64") else "x86_64"
    elif os.name == "nt":
        os_name = "windows"
        arch = "x64" if machine in ("amd64", "x86_64", "x64") else machine
    elif sys.platform.startswith("linux"):
        os_name = "linux"
        arch = (
            "arm64"
            if machine in ("arm64", "aarch64")
            else ("x86_64" if machine in ("x86_64", "amd64") else machine)
        )
    else:
        os_name = sys.platform
        arch = machine
    return os_name, arch


def get_executable_path(dist_dir: Path) -> Path:
    """Return path to the built executable binary."""
    if sys.platform == "darwin":
        return dist_dir / "dicom-organizer.app" / "Contents" / "MacOS" / "dicom-organizer"
    elif os.name == "nt":
        return dist_dir / "dicom-organizer" / "dicom-organizer.exe"
    else:
        return dist_dir / "dicom-organizer" / "dicom-organizer"


def check_no_pydicom_test_files(dist_dir: Path) -> None:
    """Verify that pydicom test data was not bundled; remove if inadvertently copied."""
    for root, dirs, _files in os.walk(dist_dir):
        if "test_files" in dirs and "pydicom" in root:
            test_files_path = Path(root) / "test_files"
            print(f"Removing bundled test files: {test_files_path}")
            shutil.rmtree(test_files_path, ignore_errors=True)


def copy_notices_and_license(dist_dir: Path) -> None:
    """Copy THIRD_PARTY_NOTICES.md and LICENSE into the distribution."""
    notices = REPO_ROOT / "THIRD_PARTY_NOTICES.md"
    license_file = REPO_ROOT / "LICENSE"

    if sys.platform == "darwin":
        resources_dir = dist_dir / "dicom-organizer.app" / "Contents" / "Resources"
        resources_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(notices, resources_dir / "THIRD_PARTY_NOTICES.md")
        shutil.copy2(license_file, resources_dir / "LICENSE")
    else:
        app_folder = dist_dir / "dicom-organizer"
        app_folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(notices, app_folder / "THIRD_PARTY_NOTICES.md")
        shutil.copy2(license_file, app_folder / "LICENSE")


def verify_macos_signature(app_path: Path) -> None:
    """Verify code signature of macOS application bundle."""
    print(f"Verifying macOS code signature: {app_path}")
    res = subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(app_path)],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(
            f"macOS codesign verification failed:\n{res.stdout}\n{res.stderr}"
        )
    print("macOS code signature is valid.")


def sign_macos(app_path: Path) -> None:
    """Sign and notarize macOS application bundle if secrets are provided, or re-sign ad-hoc."""
    cert_b64 = os.environ.get("MACOS_CERTIFICATE_P12_BASE64")
    cert_pwd = os.environ.get("MACOS_CERTIFICATE_PASSWORD")
    identity = os.environ.get("MACOS_SIGNING_IDENTITY")
    apple_id = os.environ.get("APPLE_ID")
    team_id = os.environ.get("APPLE_TEAM_ID")
    app_pwd = os.environ.get("APPLE_APP_PASSWORD")

    secrets = [cert_b64, cert_pwd, identity, apple_id, team_id, app_pwd]
    if not all(secrets):
        print("macOS signing secrets not configured. Re-signing ad-hoc after bundling resources...")
        subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", str(app_path)],
            check=True,
        )
        verify_macos_signature(app_path)
        return

    print("Signing and notarizing macOS app bundle...")
    entitlements_path = REPO_ROOT / "packaging" / "entitlements.plist"

    original_keychain: str | None = None
    try:
        kc_res = subprocess.run(
            ["security", "default-keychain"],
            capture_output=True,
            text=True,
            check=False,
        )
        if kc_res.returncode == 0 and kc_res.stdout.strip():
            original_keychain = kc_res.stdout.strip().strip('"')
    except Exception:
        pass

    with tempfile.TemporaryDirectory() as tmp:
        keychain_path = Path(tmp) / "build.keychain"
        keychain_pwd = "temporary_keychain_password"
        cert_p12 = Path(tmp) / "cert.p12"
        cert_p12.write_bytes(base64.b64decode(cert_b64))

        try:
            subprocess.run(
                ["security", "create-keychain", "-p", keychain_pwd, str(keychain_path)], check=True
            )
            subprocess.run(["security", "default-keychain", "-s", str(keychain_path)], check=True)
            subprocess.run(
                ["security", "unlock-keychain", "-p", keychain_pwd, str(keychain_path)], check=True
            )
            subprocess.run(
                [
                    "security",
                    "import",
                    str(cert_p12),
                    "-k",
                    str(keychain_path),
                    "-P",
                    cert_pwd,
                    "-T",
                    "/usr/bin/codesign",
                ],
                check=True,
            )
            subprocess.run(
                [
                    "security",
                    "set-key-partition-list",
                    "-S",
                    "apple-tool:,apple:,codesign:",
                    "-s",
                    "-k",
                    keychain_pwd,
                    str(keychain_path),
                ],
                check=True,
            )

            sign_cmd = [
                "codesign",
                "--force",
                "--deep",
                "--options",
                "runtime",
                "--timestamp",
                "--sign",
                identity,
            ]
            if entitlements_path.exists():
                sign_cmd.extend(["--entitlements", str(entitlements_path)])
            sign_cmd.append(str(app_path))

            subprocess.run(sign_cmd, check=True)

            notarize_zip = Path(tmp) / "notarize.zip"
            subprocess.run(
                ["ditto", "-c", "-k", "--keepParent", str(app_path), str(notarize_zip)], check=True
            )

            subprocess.run(
                [
                    "xcrun",
                    "notarytool",
                    "submit",
                    str(notarize_zip),
                    "--apple-id",
                    apple_id,
                    "--team-id",
                    team_id,
                    "--password",
                    app_pwd,
                    "--wait",
                ],
                check=True,
            )

            subprocess.run(["xcrun", "stapler", "staple", str(app_path)], check=True)
            verify_macos_signature(app_path)
        finally:
            if original_keychain:
                try:
                    subprocess.run(
                        ["security", "default-keychain", "-s", original_keychain], check=False
                    )
                except Exception:
                    pass



def sign_windows(exe_path: Path) -> None:
    """Sign Windows executable if certificates are provided."""
    cert_b64 = os.environ.get("WINDOWS_CERTIFICATE_PFX_BASE64")
    cert_pwd = os.environ.get("WINDOWS_CERTIFICATE_PASSWORD")

    if not all([cert_b64, cert_pwd]):
        print("Windows signing secrets not configured. Leaving unsigned (unverified).")
        return

    print("Signing Windows executable...")
    with tempfile.TemporaryDirectory() as tmp:
        pfx_path = Path(tmp) / "cert.pfx"
        pfx_path.write_bytes(base64.b64decode(cert_b64))
        timestamp_url = "http://timestamp.digicert.com"
        subprocess.run(
            [
                "signtool",
                "sign",
                "/f",
                str(pfx_path),
                "/p",
                cert_pwd,
                "/fd",
                "sha256",
                "/tr",
                timestamp_url,
                "/td",
                "sha256",
                str(exe_path),
            ],
            check=True,
        )


def create_archive(dist_dir: Path) -> Path:
    """Create zip archive and SHA256SUMS.txt."""
    os_name, arch = get_os_arch()
    zip_name = f"dicom-organizer-{APP_VERSION}-{os_name}-{arch}.zip"
    zip_path = dist_dir / zip_name

    # Remove any existing zip for this version
    for old_zip in dist_dir.glob(f"dicom-organizer-{APP_VERSION}-*.zip"):
        old_zip.unlink()

    print(f"Creating distribution archive: {zip_path}")
    if sys.platform == "darwin":
        cmd = ["ditto", "-c", "-k", "--keepParent", "dicom-organizer.app", zip_name]
        subprocess.run(cmd, cwd=dist_dir, check=True)
    else:
        import zipfile

        source_dir = dist_dir / "dicom-organizer"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(source_dir):
                for f in files:
                    file_p = Path(root) / f
                    arcname = file_p.relative_to(dist_dir)
                    zf.write(file_p, arcname)

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    sums_file = dist_dir / "SHA256SUMS.txt"
    sums_file.write_text(f"{digest}  {zip_name}\n", encoding="utf-8")
    print(f"Wrote SHA-256 digest ({digest}) to {sums_file}")
    return zip_path


def run_smoke_tests(dist_dir: Path) -> None:
    """Run smoke tests against the built binary in foreground."""
    exe = get_executable_path(dist_dir)
    print(f"Running smoke tests on executable: {exe}")
    if not exe.exists():
        raise FileNotFoundError(f"Built executable not found: {exe}")

    if sys.platform == "darwin":
        verify_macos_signature(dist_dir / "dicom-organizer.app")

    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")

    # 1. --version
    print("Testing: --version")
    res = subprocess.run(
        [str(exe), "--version"],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    print(f"--version output: {res.stdout.strip()!r}")
    if res.returncode != 0:
        raise RuntimeError(
            f"--version check failed: exit={res.returncode}\nstdout={res.stdout}\nstderr={res.stderr}"
        )
    if os.name == "nt" or sys.platform == "win32":
        # On Windows windowed executables, stdout may be empty; only check version string if output is present
        combined = (res.stdout + res.stderr).strip()
        if combined and APP_VERSION not in combined:
            raise RuntimeError(f"--version output did not match {APP_VERSION}: {combined}")
    else:
        if APP_VERSION not in (res.stdout + res.stderr):
            raise RuntimeError(
                f"--version check failed: exit={res.returncode}\nstdout={res.stdout}\nstderr={res.stderr}"
            )

    # 2. --self-test --self-test-report
    print("Testing: --self-test")
    with tempfile.TemporaryDirectory() as tmp:
        self_test_report = Path(tmp) / "self_test_report.txt"
        res = subprocess.run(
            [str(exe), "--self-test", "--self-test-report", str(self_test_report)],
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        print(f"--self-test output:\n{res.stdout.strip()}")
        if res.returncode != 0:
            raise RuntimeError(f"--self-test failed: exit={res.returncode}\nstderr={res.stderr}")
        if not self_test_report.exists() or "[PASS]" not in self_test_report.read_text(
            encoding="utf-8"
        ):
            raise RuntimeError("self-test report missing or lacking [PASS]")

        # 3. --gui-smoke-test --gui-smoke-test-report
        print("Testing: --gui-smoke-test")
        gui_report = Path(tmp) / "gui_report.txt"
        res = subprocess.run(
            [str(exe), "--gui-smoke-test", "--gui-smoke-test-report", str(gui_report)],
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        print(f"--gui-smoke-test output:\n{res.stdout.strip()}")
        if res.returncode != 0:
            raise RuntimeError(
                f"--gui-smoke-test failed: exit={res.returncode}\nstderr={res.stderr}"
            )
        if not gui_report.exists() or not gui_report.read_text(encoding="utf-8").strip():
            raise RuntimeError("gui smoke test report missing or empty")

    print("All smoke tests passed successfully!")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build standalone distribution for dicom-organizer")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run smoke tests (--version, --self-test, --gui-smoke-test) on the built binary",
    )
    args = parser.parse_args(argv)

    dist_dir = REPO_ROOT / "dist" / "standalone"
    work_dir = REPO_ROOT / "build" / "pyinstaller"
    spec_dir = REPO_ROOT / "build" / "pyinstaller"

    dist_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    entry_point = REPO_ROOT / "packaging" / "standalone_entry.py"

    pyinstaller_args = [
        "--name=dicom-organizer",
        "--windowed",
        "--onedir",
        "--noconfirm",
        "--clean",
        f"--distpath={dist_dir}",
        f"--workpath={work_dir}",
        f"--specpath={spec_dir}",
        "--collect-submodules=pydicom",
    ]
    if sys.platform == "darwin":
        pyinstaller_args.append("--osx-bundle-identifier=io.github.SugimotoKohei.dicom-organizer")

    pyinstaller_args.append(str(entry_point))

    print("Building standalone application with PyInstaller...")
    import PyInstaller.__main__

    PyInstaller.__main__.run(pyinstaller_args)

    # Clean pydicom test data if needed
    check_no_pydicom_test_files(dist_dir)

    # Bundle notices and license
    copy_notices_and_license(dist_dir)

    # Sign if secrets are present
    if sys.platform == "darwin":
        sign_macos(dist_dir / "dicom-organizer.app")
    elif os.name == "nt":
        sign_windows(dist_dir / "dicom-organizer" / "dicom-organizer.exe")

    # Create zip and checksum
    create_archive(dist_dir)

    if args.smoke_test:
        run_smoke_tests(dist_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
