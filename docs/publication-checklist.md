# Publication And Release Checklist

Use this document as the record of the first public release and as the checklist
for future releases.

## Current Publication Status

- Repository visibility: public.
- Package name: `dicom-organizer`.
- First released version: `0.1.0`.
- PyPI: <https://pypi.org/project/dicom-organizer/>
- GitHub Release:
  <https://github.com/SugimotoKohei/dicom-organizer/releases/tag/v0.1.0>
- Trusted Publishing is configured through GitHub Actions environments:
  `pypi` for PyPI and `testpypi` for TestPyPI.

## Next Release Checklist

Before tagging a future release:

```bash
uv lock --check
uv sync --locked --extra gui --group build
QT_QPA_PLATFORM=offscreen DICOM_ORGANIZER_REQUIRE_GUI=1 uv run python -m pytest
uv run ruff check
uv build
uv run dicom-organizer --help
uv run dicom-organizer --version
uv run dicom-organizer-gui --help
uv run python examples/synthetic_quickstart.py
uv run python scripts/build_standalone.py --smoke-test
# On macOS, verify bundle signature:
codesign --verify --deep --strict dist/standalone/dicom-organizer.app
```

Confirm the generated synthetic output writes `dicom_parameters.csv`,
`series_summary.csv`, and `organize_summary.json`.

Confirm `scripts/build_standalone.py --smoke-test` builds `dist/standalone/dicom-organizer.app` (or exe on Windows), packages `dist/standalone/dicom-organizer-<version>-<os>-<arch>.zip`, verifies bundle signature with `codesign --verify --deep --strict`, generates `dist/standalone/SHA256SUMS.txt`, and passes all smoke tests (`--version`, `--self-test`, and `--gui-smoke-test`).

## Standalone Application Build and Code Signing

### Secrets Configuration
The standalone build workflow (`.github/workflows/standalone.yml`) supports optional code signing and notarization when the following GitHub repository secrets are provided:

- **macOS**:
  - `MACOS_CERTIFICATE_P12_BASE64`: Base64-encoded Developer ID Application `.p12` certificate.
  - `MACOS_CERTIFICATE_PASSWORD`: Password for the `.p12` certificate.
  - `MACOS_SIGNING_IDENTITY`: Code signing identity (e.g. `Developer ID Application: Your Name (TEAMID)`).
  - `APPLE_ID`: Apple ID email for notarization.
  - `APPLE_TEAM_ID`: 10-character Apple Team ID.
  - `APPLE_APP_PASSWORD`: App-specific password generated for `notarytool`.
- **Windows**:
  - `WINDOWS_CERTIFICATE_PFX_BASE64`: Base64-encoded Authenticode `.pfx` certificate.
  - `WINDOWS_CERTIFICATE_PASSWORD`: Password for the `.pfx` certificate.

> [!WARNING]
> **Status: Unverified (未検証)**
> Official signing certificates have not yet been acquired. Consequently, the automated codesign/notarytool and signtool routines have not been verified with real certificates. In the absence of these secrets, `scripts/build_standalone.py` safely skips signing and distributes ad-hoc / unsigned bundles.

### Release Assets and Checksums
Upon pushing a release tag (`v*.*.*`), `.github/workflows/release.yml` invokes `standalone.yml` to build standalone binaries across macOS (ARM64 & Intel) and Windows (x64). The resulting archives and aggregated `SHA256SUMS.txt` are automatically attached to the GitHub Release alongside PyPI wheels and source tarballs.

### Post-Release Verification
After publishing:

1. Test Python package from PyPI:
   ```bash
   uv tool install dicom-organizer --force
   dicom-organizer --help
   dicom-organizer --version
   dicom-organizer --help | grep -- --profile
   ```
2. Test standalone zip from GitHub Release:
   - Download `dicom-organizer-<version>-<os>-<arch>.zip` and `SHA256SUMS.txt`.
   - Verify SHA256 checksum:
     ```bash
     shasum -a 256 -c SHA256SUMS.txt
     ```
   - Unpack and test:
     ```bash
     dicom-organizer.app/Contents/MacOS/dicom-organizer --version
     dicom-organizer.app/Contents/MacOS/dicom-organizer --self-test
     ```

### Downgrade and Rollback Procedure
If a critical regression is discovered in a newly published version:
1. **Desktop App Users**:
   - Instruct users to delete the current application and re-download the previous stable release zip directly from GitHub Releases (<https://github.com/SugimotoKohei/dicom-organizer/releases>).
   - The 0.1.x GUI did not save persistent settings in `QSettings`, so any settings saved by newer versions will not affect previous releases.
2. **Python Package Users**:
   - Users can revert by installing the specific previous version with `uv tool install`:
     ```bash
     uv tool install 'dicom-organizer[gui]==0.1.0' --force
     ```
3. **Repository Actions**:
   - Create a post-mortem issue and release a patch version (`vX.Y.Z+1`) rather than deleting tags, preserving immutable release history.

The release workflow uses Node 24-compatible major versions of
`actions/upload-artifact`, `actions/download-artifact`, and
`softprops/action-gh-release`. Recheck these action majors before each release.

## Repository Audit

- `git ls-files` contains only source, tests, docs, and packaging files.
- No real DICOM files are tracked.
- No generated organized output is tracked.
- No credentials, tokens, private keys, OneDrive paths, or local user paths are
  present in tracked files.
- Git history has been searched for private paths and secrets.

Current audit result:

- Tracked file list contains no real DICOM data or generated outputs.
- History search for `OneDrive`, `CloudStorage`, `/Users/`, common secret
  markers, and token-like strings found no publish-blocking matches.
- Mentions of `PatientName` and `PatientID` are expected code, docs, and
  synthetic test data.

If a future audit finds private data in history, do not change the private
repository to public. Create a clean public repository from a sanitized working
tree instead.

## First Release PyPI Name Check

The JSON API endpoint `https://pypi.org/pypi/dicom-organizer/json` returned
`404` during preparation on 2026-05-16, which indicates that the project name
was not registered at that time. The project was created during the first
release and now resolves on PyPI.

## Manual GitHub Setup Record

- Configure repository topics:
  `dicom`, `mri`, `pydicom`, `cli`, `medical-imaging`, `python`.
- Enable private vulnerability reporting if available.
- Configure the `pypi` GitHub environment with required maintainer approval.
- Configure the `testpypi` GitHub environment if using the TestPyPI workflow.
- Repository visibility has been changed to public after audit approval.

## PyPI Trusted Publishing Record

Trusted Publisher entries used for the first upload:

- PyPI project: `dicom-organizer`
- Owner/repository: `SugimotoKohei/dicom-organizer`
- Workflow: `release.yml`
- Environment: `pypi`

TestPyPI entry:

- Project: `dicom-organizer`
- Workflow: `testpypi.yml`
- Environment: `testpypi`

## First Release Smoke Test Record

The first release was validated with:

```bash
uv lock --check
uv sync --locked
uv run python -m pytest
uv run ruff check
uv build
uv run dicom-organizer --help
uv run dicom-organizer-gui --help
uv run python examples/synthetic_quickstart.py
```

The package was then installed from PyPI and smoke-tested:

```bash
uv tool install dicom-organizer --force
dicom-organizer --help
```
