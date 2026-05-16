# Contributing

Thank you for considering a contribution to `organize-dicoms`.

## Development Setup

This project uses Python 3.11 and `uv`.

```bash
uv sync --locked
uv run pytest
uv run ruff check
uv build
```

## Pull Request Expectations

- Keep changes focused and small.
- Do not commit real DICOM data, generated organized outputs, patient
  information, credentials, or local machine paths.
- Use synthetic DICOM files in tests.
- Keep CLI and GUI behavior aligned through `src/organize_dicoms/core.py`.
- Add or update tests when behavior changes.
- Update README or CHANGELOG when public behavior changes.

## Data Safety

Do not attach real DICOM files to public issues or pull requests. If a bug
requires DICOM-specific metadata, reproduce it with synthetic headers or share
only the minimal non-sensitive tag names and values needed to describe the
problem.

## Release Process

Maintainers publish releases from signed or reviewed tags. PyPI publication is
expected to use Trusted Publishing from GitHub Actions, not long-lived API
tokens.
