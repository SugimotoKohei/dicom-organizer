# Changelog

All notable changes to this project will be documented in this file.

This project follows semantic versioning before public API stability is
guaranteed. While the project is in `0.x`, CLI and CSV output changes may still
occur, but they should be documented here.

## 0.1.0 - Unreleased

- Package the DICOM organizer as the `organize-dicoms` CLI.
- Keep the `dicom-organizer` compatibility alias.
- Add optional PySide6 GUI support through the `gui` extra.
- Organize DICOM files by acquisition date and series.
- Use protocol names in default series directory names.
- Write `mri_parameters.csv`, `series_summary.csv`, and `organize_summary.json`.
- Support `--patient-mode keep/hash/drop`.
- Support repeatable `--dicom-tag` custom metadata columns.
- Add default MR acquisition metadata columns for common sequence parameters.
- Add publication metadata, safety documentation, and CI/release workflows.
