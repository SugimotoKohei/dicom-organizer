# Security Policy

## Supported Versions

Security fixes are provided for the latest released version of
`organize-dicoms`.

## Reporting a Vulnerability

Do not open a public issue with sensitive DICOM data, patient information,
credentials, or private paths.

If GitHub private vulnerability reporting is available for this repository, use
that channel. Otherwise, open a non-sensitive GitHub issue asking for a private
contact path and include no private data in the issue.

## Patient Data And PHI

`organize-dicoms` is not a complete DICOM de-identification tool. It can reduce
patient metadata written to its own CSV outputs with:

```bash
organize-dicoms --input /path/to/dicom-root --patient-mode hash
organize-dicoms --input /path/to/dicom-root --patient-mode drop
```

The default is `--patient-mode keep`, which writes `PatientName` and
`PatientID` into CSV outputs. This default exists for backward compatibility.

The tool does not rewrite DICOM headers unless a file operation copies, links,
or moves the source file. Before sharing any output, inspect the generated
folders and CSV files with your institution's privacy requirements in mind.

## Medical Use

This software is provided for research and local data organization workflows.
It is not a medical device, not intended for diagnosis, and not validated for
clinical decision making.
