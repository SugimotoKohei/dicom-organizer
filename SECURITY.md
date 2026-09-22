# Security Policy

## Supported Versions

Security fixes are provided for the latest released version of
`dicom-organizer`.

## Reporting a Vulnerability

Do not open a public issue with sensitive DICOM data, patient information,
credentials, or private paths.

If GitHub private vulnerability reporting is available for this repository, use
that channel. Otherwise, open a non-sensitive GitHub issue asking for a private
contact path and include no private data in the issue.

## Patient Data And PHI

`dicom-organizer` is designed for organizing local files and extracting acquisition parameters; it is **not** a DICOM de-identification or anonymization tool.

When handling patient information:

- **DICOM Files Are Not Anonymized**: Organizing DICOM files (via copy, link, or move) preserves the original DICOM headers completely. Patient identifiers remain inside the organized DICOM files.
- **CSV & Report Privacy Modes (`--patient-mode`)**:
  - `keep` (default): writes `PatientName` and `PatientID` verbatim to metadata CSVs.
  - `hash`: writes 16-character SHA-256 digests. Note that this is pseudonymization, not anonymization, and can be susceptible to dictionary attacks; it is not suitable for public sharing.
  - `drop`: strictly writes `N/A` for `PatientName`, `PatientID`, `PatientNameHash`, and `PatientIDHash`.
- **Other Identifiers Retained**: Study dates, Study/Series/SOP UIDs, equipment details, and original relative file paths (`SourceFileName`) remain in CSVs and `file_report.csv`. If source directory or file names contain patient identifiers, they will appear in reports.
- **Custom DICOM Tags**: If direct patient identifiers (e.g. `PatientBirthDate`, `AccessionNumber`) are specified via `--dicom-tag`, they are written verbatim regardless of `--patient-mode`.
- **List-Only Mode (`--list-only`)**: Generates parameter tables and reports without copying or creating DICOM files.

CLI usage examples:

```bash
dicom-organizer /path/to/dicom-root --patient-mode hash
dicom-organizer /path/to/dicom-root --patient-mode drop
dicom-organizer /path/to/dicom-root --list-only
```

Before sharing any outputs outside your secure local environment, follow your institution's privacy regulations and use dedicated, validated DICOM de-identification tools to remove protected health information (PHI).

## Medical Use

This software is provided for research and local data organization workflows.
It is not a medical device, not intended for diagnosis, and not validated for
clinical decision making.
