# Publication And Release Checklist

Use this document as the authoritative release procedure and checklist for `dicom-organizer` releases.

## Current Publication Status

- Repository visibility: public.
- Package name: `dicom-organizer`.
- Released versions: `0.1.0`, `0.1.1`, `0.1.2`, `0.1.3`.
- Next target version: `0.2.0`.
- PyPI: <https://pypi.org/project/dicom-organizer/>
- GitHub Releases: <https://github.com/SugimotoKohei/dicom-organizer/releases>
- Trusted Publishing is configured through GitHub Actions environments:
  `pypi` for PyPI and `testpypi` for TestPyPI.

---

## Pre-Release Verification Checklist

Execute all pre-release checks in a clean local environment before tagging:

```bash
# 1. Dependency lock verification
uv lock --check

# 2. Synchronize environment with build and GUI dependencies
uv sync --locked --extra gui --group build

# 3. Code formatting and linting
uv run ruff check

# 4. Column documentation generation check
uv run python scripts/generate_column_docs.py --check

# 5. Full test suite with strict GUI enforcement
QT_QPA_PLATFORM=offscreen DICOM_ORGANIZER_REQUIRE_GUI=1 uv run python -m pytest -q

# 6. Built-in self-test verification
uv run dicom-organizer --self-test

# 7. Distribution packaging verification
uv build

# 8. Local standalone build & smoke test (macOS Apple Silicon)
uv run python scripts/build_standalone.py --smoke-test

# 9. Verify bundle signature on macOS
codesign --verify --deep --strict dist/standalone/dicom-organizer.app
```

Confirm that:
- `uv build` generates valid source distribution (`.tar.gz`) and binary wheel (`.whl`).
- `scripts/generate_column_docs.py --check` reports `docs/csv-columns.md is up to date.` without differences.
- `scripts/build_standalone.py --smoke-test` packages `dist/standalone/dicom-organizer-<version>-<os>-<arch>.zip` (bundling Python 3.14), checks bundle signature with `codesign --verify --deep --strict`, generates `SHA256SUMS.txt`, and passes all smoke tests (`--version`, `--self-test`, `--gui-smoke-test`).

---

## Tagging and CI Verification

### 1. Tagging the Release

Once all local checks pass, create an annotated Git tag and push it:

```bash
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

### 2. CI Workflow and Cross-Platform Verification

Pushing the release tag triggers `.github/workflows/release.yml` and `.github/workflows/standalone.yml`.

> [!IMPORTANT]
> **Windows and Intel Mac CI Verification**:
> Standalone applications for **Windows** (x64) and **Intel Mac** (x86_64) are built with Python 3.14 for the first time on GitHub Actions CI runners (since local development is on Apple Silicon macOS).
> - Always verify that CI runs on `windows-latest` (Windows x64), `macos-15` (Apple Silicon arm64), and `macos-15-intel` (Intel x86_64) complete successfully.
> - Verify that the standalone self-test (`--self-test`) and CLI version checks succeed on both Windows and Intel CI runners before finalizing the release.
> - Confirm that release artifacts (`.zip` archives and aggregated `SHA256SUMS.txt`) are generated and attached to the GitHub Release draft.

---

## GitHub Release Notes Preparation

Draft the GitHub Release text using the contents of `CHANGELOG.md` under `## 0.2.0`:

1. **Highlights**: Summarize the 3–5 key capabilities (such as `--list-only` mode, the redesigned task-oriented GUI, and standalone apps).
2. **Breaking Changes**: Detail directory layout changes, strict privacy (`--patient-mode drop`), granular skip reason handling (`skipped_non_dicom`), and CSV column changes, linking to [upgrade-guide.md](upgrade-guide.md).
3. **Important Notice on Unsigned Bundles (未署名バイナリに関する注意)**:
   - Standalone applications are distributed as ad-hoc / **unsigned** (未署名) packages.
   - On macOS, Gatekeeper may block first-time launch. Users must follow the security exemption instructions in [install.md](install.md).
   - On Windows, Microsoft Defender SmartScreen may display an unrecognized app prompt. Instruct users to refer to [install.md](install.md).
4. **Links**: Include links to [install.md](install.md) and [upgrade-guide.md](upgrade-guide.md).

---

## Post-Release Verification

### 1. PyPI Package Verification

Immediately after PyPI publish workflow completes:

```bash
# Install specific release version in a fresh environment
uv tool install dicom-organizer==0.2.0 --force

# Verify version
dicom-organizer --version

# Verify self-test diagnostic
dicom-organizer --self-test
```

### 2. Standalone Binary Verification

Download released assets from GitHub Releases and check:

```bash
# Verify checksums
shasum -a 256 -c SHA256SUMS.txt

# Test standalone application binary
./dicom-organizer.app/Contents/MacOS/dicom-organizer --version
./dicom-organizer.app/Contents/MacOS/dicom-organizer --self-test
```

---

## Rollback and Mitigation Procedure

If a critical regression, data safety issue, or packaging failure is detected in a published release:

### 1. PyPI Release Yanking
- PyPI does not allow re-uploading an existing version number.
- In case of critical defects, **yank** the release on PyPI:
  ```bash
  # Via PyPI web interface or twine / API
  # Navigate to https://pypi.org/manage/project/dicom-organizer/release/0.2.0/
  # Select "Options" -> "Yank release" and provide an explanatory reason
  ```
  Yanking marks the version as deprecated and prevents automatic installation by package resolvers while preserving builds for pinned users.

### 2. GitHub Release Retraction
- Mark the GitHub Release as a "Pre-release" or edit the release description to display a prominent warning banner.
- If severe, remove downloadable `.zip` assets from the release to prevent new downloads.

### 3. User Downgrade Guidance
Provide clear instructions for users to revert to the previous stable version (e.g. 0.1.3):
- **Python Users**:
  ```bash
  uv tool install --force 'dicom-organizer[gui]==0.1.3'
  ```
- **Desktop App Users**:
  Instruct users to refer to [upgrade-guide.md](upgrade-guide.md) and install the previous stable version. Remind users not to organize into 0.2.0 output directories with 0.1.x.

---

## Historical Publication Records

### First Release (v0.1.0)
- PyPI project creation date: 2026-05-17.
- First public release verified with synthetic datasets and clean audit.
- Trusted Publishing configured with GitHub Actions environment `pypi`.
