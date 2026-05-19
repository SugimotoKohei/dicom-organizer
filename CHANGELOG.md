# Changelog

All notable changes to this project will be documented in this file.

This project follows semantic versioning before public API stability is
guaranteed. While the project is in `0.x`, CLI and CSV output changes may still
occur, but they should be documented here.

## 0.1.4 - Unreleased

- Allow the input directory to be passed as a positional argument, while keeping
  `-i` and `--input` for compatibility.
- Add common short CLI options for output, profile, dry-run, force-read, limit,
  custom DICOM tags, and verbose output.
- Update CLI examples to prefer `dicom-organizer /path/to/dicom-root`.

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
