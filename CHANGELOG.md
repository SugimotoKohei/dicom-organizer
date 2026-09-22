# Changelog

All notable changes to this project will be documented in this file.

This project follows semantic versioning before public API stability is
guaranteed (see [docs/stability.md](docs/stability.md)). While the project is in `0.x`, CLI and CSV output changes may still
occur, but they should be documented here.

## 0.2.0 - Unreleased

### Highlights
- List imaging parameters without copying files: `--list-only` mode outputs tabular acquisition parameters directly to CSV, ideal for quick protocol inspection and data inventory.
- Redesigned task-oriented GUI: clean start screen with 3 clear goals ("List imaging parameters", "Copy and organize", "Preview before organizing"), synthetic test data generator, drag-and-drop, and English/Japanese localization.
- Standalone desktop apps and self-contained distribution: ready-to-run packages without local Python installation, supported by built-in `--self-test` verification.
- Granular file tracking and duplicate handling: root-level `all_series_summary.csv` and `file_report.csv` record per-file status, skip reasons, and SHA-256 digests while safely skipping identical duplicate instances.

### Breaking changes
- Default folder hierarchy: changed to `<output>/<Device>/<StudyDate>/<SeriesNumber>_<Label>/` (`--layout device-date`), grouping by scanner model and ordering by `StudyDate` instead of `AcquisitionDate`. Do not reuse 0.1.x output directories; specify a new empty destination directory (see [docs/upgrade-guide.md](docs/upgrade-guide.md#1-default-folder-hierarchy-breaking-change)).
- Strict privacy mode semantics (`--patient-mode drop`): `PatientName`, `PatientID`, `PatientNameHash`, and `PatientIDHash` are all written as `N/A` instead of retaining SHA-256 hash digests (see [docs/upgrade-guide.md](docs/upgrade-guide.md#4-strict-privacy-mode-semantics---patient-mode-drop-breaking-change)).
- Granular skip reason classification (`skipped_non_dicom`): `skipped_non_dicom` now strictly counts files with reason code `not_dicom`. All candidate skips are classified into 9 explicit reason codes in `organize_summary.json` and `file_report.csv` (see [docs/upgrade-guide.md](docs/upgrade-guide.md#5-granular-skip-reason-classification-skipped_non_dicom-breaking-change)).
- CSV column updates and removals: `SeriesUIDHash` column was removed from `series_summary.csv` (identify series via `SeriesUID` or `SeriesFolder`), `CoilElementCount` outputs `N/A` instead of `0` when absent, and 15 new columns including `StudyFolder` and `SeriesFolder` were added to `dicom_parameters.csv` (see [docs/upgrade-guide.md](docs/upgrade-guide.md#6-csv-column-changes)).
- Summary schema version 2: `organize_summary.json` updated with `output_schema_version: 2` and 22 new metadata keys including environment provenance, skip breakdowns, and options snapshots (see [docs/upgrade-guide.md](docs/upgrade-guide.md#8-organize_summaryjson)).

### Added
- Support running CLI via `python -m dicom_organizer` and `python -m dicom_organizer.cli` (`src/dicom_organizer/__main__.py`).
- Add DICOM support verification suite (`tests/test_support_matrix.py`) covering compressed transfer syntaxes (JPEG Baseline and JPEG 2000 Lossless with SHA-256 byte preservation), character sets (UTF-8 `ISO_IR 192` and Japanese `ISO 2022 IR 87` with `safe_name()` folder verification), non-image objects (Basic Text SR and RTSTRUCT verified via `file_report.csv`), preamble-less streams under force-read, DICOMDIR handling via `pydicom.fileset.FileSet`, Enhanced MR functional groups, and vendor private tag fallbacks.
- Add multi-mode performance benchmark tool (`scripts/benchmark.py`) measuring throughput (files/s) and peak RSS memory via `os.wait4` across dry-run, list-only, copy, and copy+checksum modes with Markdown and JSON exports.
- Add headless screenshot and demo GIF renderer (`scripts/render_screenshots.py`) capturing light-themed, privacy-sanitized GUI states and dynamically generating `docs/images/before-after.md` dataset comparisons.
- Add cross-scanner protocol comparison script (`examples/compare_protocols.py`) grouping series by description or protocol name and flagging divergent acquisition parameters.
- Add downstream batch conversion helper (`examples/dcm2niix_batch.py`) to prepare and execute `dcm2niix` commands from organized DICOM summaries.
- Redesign the PySide6 GUI around a task-oriented first-time experience (`src/dicom_organizer/gui.py`), featuring a stacked start screen with 3 clear goals: "List imaging parameters" (`list`, `list_only=True`), "Copy and organize" (`organize`, `action="copy"`), and "Preview before organizing" (`preview`, `dry_run=True`), along with instant synthetic sample dataset testing.
- Add internationalization module (`src/dicom_organizer/i18n.py`) providing full Japanese and English localization for all GUI elements, friendly skip/status reason labels and explanations, and staged progress messages.
- Add an always-visible patient information notice panel in the GUI dynamically reflecting `patient_data_notices()`, making retained identifiers and lack of DICOM modification transparent across `keep`, `hash`, and `drop` modes.
- Support folder and file drag-and-drop anywhere onto the GUI window, automatic destination folder derivation (`organized_list` or `organized`), and manual destination override preservation.
- Add worker-thread execution with throttled progress updates, determinate/indeterminate progress bar, graceful cancellation (`threading.Event`), and one-click resume (`--if-exists skip`) for interrupted or cancelled runs.
- Add GUI menu support for configuration file import/export (`load_config` / `config_to_toml`), instant language switching (Japanese / English), font scaling (Normal / Large 1.25x), interactive glossary dialog, in-app self-test execution, and sanitized diagnostics export to clipboard.
- Support headless CLI flags in `gui.main()` (`--self-test`, `--self-test-report`, `--version`, `--diagnostics`, `--help`) without instantiating windows.
- Add column dictionary and machine-readable schema (`src/dicom_organizer/columns.py`, `ColumnSpec`, `COLUMN_SPECS`, `column_spec()`, and `schema_document()`) defining meanings, units, sources, levels, missing (`N/A`) conditions, profile scopes, and `absent_value` for all 100 CSV columns.
- Add `--print-schema` CLI option to export the schema document and column conventions as formatted JSON without requiring input directories.
- Add `scripts/generate_column_docs.py` documentation generator with `--check` mode, creating `docs/csv-columns.md` in both English and Japanese.
- Add Enhanced / multi-frame DICOM support: extract 13 key imaging parameters from Shared and Per-Frame Functional Groups when classic attributes are absent, preserve distinct frame-varying values with `|` delimiters in frame order, and add `NumberOfFrames` and `FrameVaryingAttributes` common columns to both `dicom_parameters.csv` and `series_summary.csv`.
- Add facility-wide TOML configuration file support via `--config PATH` and the `DICOM_ORGANIZER_CONFIG` environment variable, with strict schema/type validation, relative `output` path resolution against config directory, and CLI precedence merging.
- Add `--print-config` command to export current effective configuration (defaults + config + CLI) as valid TOML for template generation.
- Track `config_file` in `OrganizeOptions` and record its path in `organize_summary.json`.
- Add deterministic synthetic sample dataset generator (`src/dicom_organizer/sample_data.py`, `create_sample_dataset()`) providing realistic multi-scanner, multi-study messy test datasets with pixel data and expected metrics.
- Add self-test diagnostic tool via `--self-test` and `--self-test-report PATH` (`src/dicom_organizer/selftest.py`, `run_self_test()`) to verify standard organization, list-only, and dry-run behaviors using ephemeral sample data.
- Add bug-report environment diagnostics via `--diagnostics` and `diagnostics_lines()`, sanitizing home directory paths (`~`) without including patient or input directory information.
- Add `--list-only` mode to write metadata parameter tables and reports without copying or materializing DICOM files (defaulting to `<input>/organized_list`).
- Add `StudyFolder` and `SeriesFolder` columns to both `dicom_parameters.csv` and `series_summary.csv`.
- Add run-level `all_series_summary.csv` written directly under output root in both regular organization and list-only mode, concatenating all series summaries across studies and runs.
- Add organization layout presets via `--layout`: `device-date` (default), `study` (`<StudyDate>_<StudyKey>`), and `patient-study` (`<PatientKey>/<StudyDate>_<StudyKey>`).
- Add privacy notice system (`messages.py`, `patient_data_notices()`) with English and Japanese guidance on retained identifiers, recorded in `organize_summary.json` and printed on CLI execution.
- Add warnings when direct patient identifier tags are specified via `--dicom-tag` under non-keep patient modes.
- Add granular skip reason classification (`SKIP_REASONS`) and `classify_dicom_file` to distinguish non-DICOM files, DICOMDIR, missing required UIDs, read errors, permission errors, hidden files, and duplicates.
- Add `file_report.csv` output to root directory providing per-file tracking of source-to-destination mappings, status, reasons, and file hashes.
- Add `SOPInstanceUID` deduplication: skip identical duplicates without inflating `FileCount`, place conflicting duplicates with `duplicate_conflict` tracking, maintain content-hash history across multi-duplicate chains, and record SHA-256 digests on duplicate comparisons.
- Add pre-existing output collision warnings and `existing_output_conflicts` tracking during dry runs with `--if-exists error`.
- Add staged progress event API (`ProgressEvent`) and console progress display (`--no-progress` to disable).
- Support run cancellation and graceful recovery from interrupts and exceptions, recording partial runs as `cancelled`, `interrupted`, or `failed` and enabling resume via `--if-exists skip`.
- Add pre-check for destination free disk space before copying or cross-device moves (`--no-space-check` to disable).
- Add copy integrity verification and optional SHA-256 checksumming via `--checksum`.
- Add `ScanDuration` (formatted as `HH:MM:SS`) and `ScanDurationSource` columns to `dicom_parameters.csv` and `series_summary.csv`.
- Allow the input directory to be passed as a positional argument, while keeping `-i` and `--input` for compatibility.
- Add common short CLI options for output, profile, dry-run, force-read, limit, custom DICOM tags, and verbose output.

### Changed
- Enhance GUI results display with 1-sentence plain-language conclusions (accurately reflecting CSV target images and image series in list-only/preview modes), categorized skip/unhandled reason table, series preview table, quick-open folder/CSV buttons, and direct transition from preview to execution.
- Refine GUI styling for dark mode support (guaranteeing >= 4.5 contrast ratios on color-coded panels, action bars, and secondary labels/card texts via dynamically computed palette blend colors), eliminate placeholder-text reliance for dim text, eliminate pixel-fixed font sizes to fully support dynamic font scaling, ensure full word-wrapping in counts tables, and enforce expanding form fields on macOS.
- Rewrite `tests/test_gui.py` covering 13 test scenarios in offscreen mode with strict `DICOM_ORGANIZER_REQUIRE_GUI=1` enforcement.
- Strictly represent missing values as `N/A` in CSV tables: write `N/A` to `AcquisitionDate` when both `AcquisitionDate` and `StudyDate` are absent (folder names retain `unknown_date`), write `N/A` to `InstanceNumber` when absent from header (filename templates retain sequence counter), and set `EchoCount` and `CoilElementCount` to `N/A` rather than `0` when no target values exist.
- Replace always-empty `ThermalIndex` column in US profile with three standard DICOM attributes: `SoftTissueThermalIndex (0018,5027)`, `BoneThermalIndex (0018,5024)`, and `CranialThermalIndex (0018,5026)`.
- Restrict Siemens private metadata columns (`SiemensChannelMixing`, `SiemensCoilElement`, `SiemensIceDims`, `SiemensIceDimChannel`, `SiemensIceDimEcho`) to objects whose `Manufacturer` contains `siemens` (case-insensitive), outputting `N/A` otherwise.
- Enhance multi-echo TE aggregation: split `TE_ms` values by `|` before counting unique echo times to correctly calculate `EchoCount` and `EchoTimes_ms` on Enhanced multi-echo series.
- Update `examples/synthetic_quickstart.py` to use `create_sample_dataset()`.
- Sort `file_report.csv` rows by `SourceFileName` ascending.
- Enable force-read by default and add `--no-force-read` for strict standard DICOM header parsing.
- Preserve existing CSV rows on rerun with `--if-exists skip`, dropping rows only when output files no longer exist.

### Fixed
- Make file materialization atomic using temporary files and `os.replace` to prevent losing previous outputs on failure.
- Sanitize `StudyDate` and verify all written paths stay strictly within `output_root` to prevent directory escape.
- Ensure series directory names are unique across all series, reserving existing series names to prevent collisions.
- Wire CLI `-t/--dicom-tag/--tag` option to `dicom_tags` so custom tags reach metadata CSVs.
- Resolve `input_root` and `output_root` in `OrganizeOptions` to absolute paths, ensuring valid symlinks with relative paths.
- Scope Philips numeric series anchor label lookup to the same `StudyInstanceUID`.

### Documentation
- Add bilingual documentation suite across `docs/` and repository root:
  - `README.md`: value-oriented overview with before-after comparisons, GIF demo, quickstart guides, output explanations, and privacy warnings.
  - `SUPPORT.md` & `GOVERNANCE.md`: clear support routing (FAQ -> docs -> Discussions -> email `sugimotokouhei@gmail.com`), PHI submission warnings, project governance, and maintainer roadmap.
  - `SECURITY.md` & `CONTRIBUTING.md`: updated vulnerability disclosure contact and developer guidance including GUI testing prerequisites.
  - `docs/usage.md`: full CLI usage guide migrated from original README plus advanced options (`--list-only`, `--layout`, `--config`, `--checksum`, `--diagnostics`, `--self-test`).
  - `docs/positioning.md`: target user personas, definition of default adoption, success metrics, and out-of-scope boundaries.
  - `docs/support-matrix.md`: multi-tiered DICOM capability matrix grounded in explicit test assertions and real-scanner multi-vendor validation.
  - `docs/validation.md`: automated CI test matrix across 3 OSes, real-world scanner verification table across 5 MRI models, and unverified boundary disclosures.
  - `docs/performance.md`: benchmark methodology, memory scaling analysis, and throughput figures traced directly to empirical benchmark facts.
  - `docs/privacy.md`: privacy analysis across `keep`, `hash`, and `drop` modes, retained identifiers, and DICOM PS3.15 Annex E anonymization guidance.
  - `docs/deployment-guide.md`: one-page institutional IT guide covering permissions, zero network communication, security boundary checklist, and unattended verification.
  - `docs/stability.md`: versioning compatibility guarantees, schema deprecation rules, and empirical criteria for Alpha -> Beta -> Stable progression.
  - `docs/upgrade-guide.md` & `docs/faq.md`: 0.1.x to 0.2.0 upgrade guidance and troubleshooting for common user questions and platform quirks.
  - `docs/workflows/`: six downstream integration guides covering cross-scanner protocol comparison, 3D Slicer import, dcm2niix conversion, research sharing, Orthanc upload, and repeated data ingestion.
  - `docs/research/`: user research plan and interview record templates for empirical adoption validation.
  - `.github/`: structured issue templates (`bug_report.yml`, `verification_report.yml`, `feature_request.yml`), template config with contact routes, and pull request template.
- Add `examples/README.md` documenting synthetic testing and workflow integration scripts in English and Japanese.
- Add links to `docs/csv-columns.md` in `docs/csv-schema.md`.
- Add `docs/configuration.md` and expand `docs/csv-schema.md` in both English and Japanese.
- Clarify that `--if-exists skip` is optional, not the default.
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
