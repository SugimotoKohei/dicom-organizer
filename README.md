# organize-dicoms

[![CI](https://github.com/SugimotoKohei/organize-dicoms/actions/workflows/ci.yml/badge.svg)](https://github.com/SugimotoKohei/organize-dicoms/actions/workflows/ci.yml)

`organize-dicoms` is a local command-line tool for organizing DICOM files into a
stable folder layout and writing MRI metadata CSV files for review.

It reads DICOM headers with `pydicom`, keeps source files untouched by default,
and writes:

```text
organized/<AcquisitionDate>/<SeriesNumber>_<ProtocolName>/000001.dcm
organized/<AcquisitionDate>/mri_parameters.csv
organized/<AcquisitionDate>/series_summary.csv
organized/organize_summary.json
```

The CLI is the primary interface. A PySide6 GUI is available as an optional
extra.

## Important Safety Notes

This project is intended for research and local data management workflows. It is
not a medical device, not intended for diagnosis, and not a complete DICOM
de-identification system.

The default patient mode is `keep` for compatibility. That means `PatientName`
and `PatientID` are written to metadata CSV files unless you choose another
mode. Before sharing output folders or CSV files, use one of:

```bash
organize-dicoms --input /path/to/dicom-root --patient-mode hash
organize-dicoms --input /path/to/dicom-root --patient-mode drop
```

Always inspect generated CSV files before sharing them outside your local
environment.

## Installation

From PyPI, after the first public release:

```bash
uv tool install organize-dicoms
```

Alternative installers:

```bash
pipx install organize-dicoms
pip install organize-dicoms
```

From a local checkout:

```bash
uv sync
uv run organize-dicoms --help
```

For editable command-line use from this repository:

```bash
uv tool install --editable . --force
organize-dicoms --help
dicom-organizer --help
```

`dicom-organizer` is a compatibility alias. Prefer `organize-dicoms` for new
workflows.

## Quick Start

Run a dry run first:

```bash
organize-dicoms --input /path/to/dicom-root --dry-run --force-read --if-exists skip
```

If the summary looks correct, write the organized copy:

```bash
organize-dicoms --input /path/to/dicom-root --force-read --if-exists skip
```

By default, the output directory is `<input>/organized`. Source files are copied,
not moved.

To move files instead of copying them, you must explicitly confirm the move:

```bash
organize-dicoms --input /path/to/dicom-root --action move --confirm-move
```

## Output Metadata

`mri_parameters.csv` contains one row per organized DICOM instance.
`series_summary.csv` contains one row per series.

Default MRI metadata includes common acquisition parameters such as:

- TR and TE
- FOV and matrix
- pixel bandwidth
- echo train length
- flip angle
- slice thickness and spacing
- number of averages
- magnetic field strength
- scanning sequence and sequence variant
- `SequenceName`
- `InversionTime_ms`
- `EchoNumbers`
- `AcquisitionMatrix`
- `NumberOfPhaseEncodingSteps`
- `PercentSampling`
- `PercentPhaseFOV`
- `SAR`

Phase encoding direction is not included by default because vendor support is
inconsistent. Add it explicitly when needed.

## Custom DICOM Tags

Use repeatable `--dicom-tag` or `--tag` arguments to append DICOM tag values to
`mri_parameters.csv`:

```bash
organize-dicoms --input /path/to/dicom-root \
  --dicom-tag EchoTime \
  --dicom-tag 0018,0080 \
  --dicom-tag CustomPhase=0018,1312 \
  --dicom-tag InPlanePhaseEncodingDirection
```

Accepted formats:

- DICOM keyword, such as `EchoTime`
- numeric tag, such as `0018,0080`
- parenthesized numeric tag, such as `(0018,0080)`
- hex tag, such as `0x00180080`
- explicit column mapping, such as `ColumnName=0018,0080`

Missing values are written as `N/A`.

## Patient Metadata Modes

```bash
organize-dicoms --input /path/to/dicom-root --patient-mode keep
organize-dicoms --input /path/to/dicom-root --patient-mode hash
organize-dicoms --input /path/to/dicom-root --patient-mode drop
```

- `keep`: write `PatientName` and `PatientID` as found in the DICOM headers.
- `hash`: replace both values with `sha256:<digest>`.
- `drop`: write `N/A`.

`PatientNameHash` and `PatientIDHash` are written for checking in all modes.

## Optional GUI

Install the GUI extra only when needed:

```bash
uv tool install 'organize-dicoms[gui]'
organize-dicoms-gui
```

From a local checkout:

```bash
uv tool install --editable '.[gui]' --force
organize-dicoms-gui
```

The GUI uses the same core processing code as the CLI.

## Synthetic Example

This repository does not include real DICOM data. From a local checkout, test
the command with synthetic DICOM files:

```bash
uv run python examples/synthetic_quickstart.py
```

The script creates a temporary synthetic DICOM tree, runs `organize-dicoms`, and
prints the output location.

## Common Issues

`Input directory does not exist`

: Check the `--input` path. Paths containing spaces should be quoted.

`Output directory must be different from input directory`

: Choose an output folder other than the input root.

`Target exists`

: Use `--if-exists skip` for repeated runs, `rename` for a second copy, or
  `overwrite` only when you intentionally want to replace files.

`PySide6 is not installed`

: Install the GUI extra with `organize-dicoms[gui]`. The CLI does not require
  PySide6.

## Development

```bash
uv sync --locked
uv run pytest
uv run ruff check
uv build
```

Release builds are published from GitHub Actions by tag. PyPI publishing should
use Trusted Publishing rather than long-lived API tokens.

## License

MIT License. See [LICENSE](LICENSE).
