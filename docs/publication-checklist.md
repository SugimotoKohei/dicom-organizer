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
uv sync --locked
uv run python -m pytest
uv run ruff check
uv build
uv run dicom-organizer --help
uv run dicom-organizer --version
uv run dicom-organizer-gui --help
uv run python examples/synthetic_quickstart.py
```

Confirm the generated synthetic output writes `dicom_parameters.csv`,
`series_summary.csv`, and `organize_summary.json`.

After publishing:

```bash
uv tool install dicom-organizer --force
dicom-organizer --help
dicom-organizer --version
dicom-organizer --help | grep -- --profile
```

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
