# Publication Checklist

Use this checklist before making the repository public or publishing to PyPI.

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

## PyPI Name

The JSON API endpoint `https://pypi.org/pypi/organize-dicoms/json` returned
`404` during preparation on 2026-05-16, which indicates that the project name
was not registered at that time. Recheck immediately before the first release.

## Manual GitHub Setup

- Configure repository topics:
  `dicom`, `mri`, `pydicom`, `cli`, `medical-imaging`, `python`.
- Enable private vulnerability reporting if available.
- Configure the `pypi` GitHub environment with required maintainer approval.
- Configure the `testpypi` GitHub environment if using the TestPyPI workflow.
- After audit approval, change repository visibility to public.

## PyPI Trusted Publishing

Create pending Trusted Publisher entries before the first upload:

- PyPI project: `organize-dicoms`
- Owner/repository: `SugimotoKohei/organize-dicoms`
- Workflow: `release.yml`
- Environment: `pypi`

Optional TestPyPI entry:

- Project: `organize-dicoms`
- Workflow: `testpypi.yml`
- Environment: `testpypi`

## Release Smoke Test

Before tagging:

```bash
uv lock --check
uv sync --locked
uv run pytest
uv run ruff check
uv build
uv run organize-dicoms --help
uv run dicom-organizer --help
uv run organize-dicoms-gui --help
uv run python examples/synthetic_quickstart.py
```

After publishing:

```bash
uv tool install organize-dicoms --force
organize-dicoms --help
```
