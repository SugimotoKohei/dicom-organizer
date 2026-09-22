# Changelog

All notable changes to this project will be documented in this file.

This project follows semantic versioning before public API stability is
guaranteed. While the project is in `0.x`, CLI and CSV output changes may still
occur, but they should be documented here.

## 0.2.0 - Unreleased

- Add Enhanced / multi-frame DICOM support: extract 13 key imaging parameters from Shared and Per-Frame Functional Groups when classic attributes are absent, preserve distinct frame-varying values with `|` delimiters in frame order, and add `NumberOfFrames` and `FrameVaryingAttributes` common columns to both `dicom_parameters.csv` and `series_summary.csv`.
- Enhance multi-echo TE aggregation: split `TE_ms` values by `|` before counting unique echo times to correctly calculate `EchoCount` and `EchoTimes_ms` on Enhanced multi-echo series.
- Add facility-wide TOML configuration file support via `--config PATH` and the `DICOM_ORGANIZER_CONFIG` environment variable, with strict schema/type validation, relative `output` path resolution against config directory, and CLI precedence merging.
- Add `--print-config` command to export current effective configuration (defaults + config + CLI) as valid TOML for template generation.
- Track `config_file` in `OrganizeOptions` and record its path in `organize_summary.json`.
- Add deterministic synthetic sample dataset generator (`src/dicom_organizer/sample_data.py`, `create_sample_dataset()`) providing realistic multi-scanner, multi-study messy test datasets with pixel data and expected metrics.
- Add self-test diagnostic tool via `--self-test` and `--self-test-report PATH` (`src/dicom_organizer/selftest.py`, `run_self_test()`) to verify standard organization, list-only, and dry-run behaviors using ephemeral sample data.
- Add bug-report environment diagnostics via `--diagnostics` and `diagnostics_lines()`, sanitizing home directory paths (`~`) without including patient or input directory information.
- Update `examples/synthetic_quickstart.py` to use `create_sample_dataset()`.
- Add `docs/configuration.md` and expand `docs/csv-schema.md` in both English and Japanese.
- Add `--list-only` mode to write metadata parameter tables and reports without copying or materializing DICOM files (defaulting to `<input>/organized_list`).
- Add `StudyFolder` and `SeriesFolder` columns to both `dicom_parameters.csv` and `series_summary.csv`.
- Add run-level `all_series_summary.csv` written directly under output root in both regular organization and list-only mode, concatenating all series summaries across studies and runs.
- Add organization layout presets via `--layout`: `device-date` (default), `study` (`<StudyDate>_<StudyKey>`), and `patient-study` (`<PatientKey>/<StudyDate>_<StudyKey>`).
- Enforce strict `--patient-mode drop` semantics: omit `PatientName`, `PatientID`, `PatientNameHash`, and `PatientIDHash` (all written as `N/A`, breaking change from previously retaining hash digests).
- Add privacy notice system (`messages.py`, `patient_data_notices()`) with English and Japanese guidance on retained identifiers, recorded in `organize_summary.json` and printed on CLI execution.
- Add warnings when direct patient identifier tags are specified via `--dicom-tag` under non-keep patient modes.
- Add granular skip reason classification (`SKIP_REASONS`) and `classify_dicom_file` to distinguish non-DICOM files, DICOMDIR, missing required UIDs, read errors, permission errors, hidden files, and duplicates.
- Restrict `skipped_non_dicom` count strictly to files with `not_dicom` reason (breaking change from previously counting all unreadable candidates).
- Add `file_report.csv` output to root directory providing per-file tracking of source-to-destination mappings, status, reasons, and file hashes.
- Add `SOPInstanceUID` deduplication: skip identical duplicates without inflating `FileCount`, place conflicting duplicates with `duplicate_conflict` tracking, maintain content-hash history across multi-duplicate chains, and record SHA-256 digests on duplicate comparisons.
- Add pre-existing output collision warnings and `existing_output_conflicts` tracking during dry runs with `--if-exists error`.
- Sort `file_report.csv` rows by `SourceFileName` ascending.
- Add staged progress event API (`ProgressEvent`) and console progress display (`--no-progress` to disable).
- Support run cancellation and graceful recovery from interrupts and exceptions, recording partial runs as `cancelled`, `interrupted`, or `failed` and enabling resume via `--if-exists skip`.
- Add pre-check for destination free disk space before copying or cross-device moves (`--no-space-check` to disable).
- Add copy integrity verification and optional SHA-256 checksumming via `--checksum`.
- Update `organize_summary.json` to schema version 2 with environment provenance, complete options snapshot, report listings, and failure diagnosis.
- Add `ScanDuration` (formatted as `HH:MM:SS`) and `ScanDurationSource` columns to `dicom_parameters.csv` and `series_summary.csv`.
- Restructure default output folder hierarchy to `organized/<Device>/<StudyDate>/<SeriesNumber>_<SeriesFolderLabel>/`.
- Remove `SeriesUIDHash` column from metadata CSVs.
- Sanitize `StudyDate` and verify all written paths stay strictly within `output_root` to prevent directory escape.
- Ensure series directory names are unique across all series, reserving existing series names to prevent collisions.
- Make file materialization atomic using temporary files and `os.replace` to prevent losing previous outputs on failure.
- Preserve existing CSV rows on rerun with `--if-exists skip`, dropping rows only when output files no longer exist.
- Wire CLI `-t/--dicom-tag/--tag` option to `dicom_tags` so custom tags reach metadata CSVs.
- Resolve `input_root` and `output_root` in `OrganizeOptions` to absolute paths, ensuring valid symlinks with relative paths.
- Scope Philips numeric series anchor label lookup to the same `StudyInstanceUID`.
- Allow the input directory to be passed as a positional argument, while keeping
  `-i` and `--input` for compatibility.
- Add common short CLI options for output, profile, dry-run, force-read, limit,
  custom DICOM tags, and verbose output.
- Update CLI examples to prefer `dicom-organizer /path/to/dicom-root`.
- Enable force-read by default and add `--no-force-read` for strict standard
  DICOM header parsing.
- Clarify that `--if-exists skip` is optional, not the default.

## 0.1.3 - 2026-05-20

- Improve the PySide6 GUI with a persistent summary panel, clearer dry-run
  status, modality count formatting, and shorter error messages with full
  details kept in the log.
- Add visible GUI warnings for `patient-mode=keep`, `action=move`, and
  `if-exists=overwrite`.
- Collapse advanced GUI options by default so routine runs focus on paths,
  profile, action, and patient metadata handling.
- Add `dicom-organizer-gui-app` to create a lightweight macOS `.app` launcher
  for the installed GUI.
- Add GUI regression tests for the initial safety guidance and dry-run summary
  display, plus launcher bundle generation tests.

## 0.1.2 - 2026-05-19

- Add modality-level summary counts for organized, CSV-target, and CSV-excluded
  files.
- Add CSV schema documentation for mixed modality inputs and profile behavior.
- Expand mixed modality regression tests for MR, CT, US, XA, PT, and non-image
  exclusions.

## 0.1.1 - 2026-05-17

- Add post-release documentation, clearer run summaries, and CLI version output.

## 0.1.0 - 2026-05-17

- Package the project as `dicom-organizer`.
- Provide the `dicom-organizer` CLI.
- Add optional PySide6 GUI support through the `gui` extra.
- Organize DICOM files by acquisition date and series.
- Use normalized series labels in default series directory names, with vendor-aware
  handling for Philips, GE, Canon, and Toshiba-family metadata.
- Write `dicom_parameters.csv`, `series_summary.csv`, and `organize_summary.json`.
- Support metadata profiles with `--profile auto/generic/mr/ct/us/xa/pt`.
- Support `--patient-mode keep/hash/drop`.
- Support repeatable `--dicom-tag` custom metadata columns.
- Add modality-aware acquisition metadata columns for common MR, CT, US, XA, and
  PT parameters.
- Add publication metadata, safety documentation, and CI/release workflows.
