# Sample DICOM Organization Example (Before & After) / 整理前後の実例

## 1. Input Structure / 整理前の入力ツリー

The raw input directory contains DICOM slices exported across nested media folders (`EXPORT/DISK1/...`), identical copies in `BACKUP/` (`BACKUP/IM00001`), and non-DICOM documentation files (`README.TXT`):
整理前の入力フォルダには、入れ子になった媒体フォルダ（`EXPORT/DISK1/...`）の DICOM 画像、`BACKUP/` にある同一画像のコピー（`BACKUP/IM00001`）、および DICOM 以外の説明ファイル（`README.TXT`）が含まれています:

```text
sample_dataset/
├── BACKUP/
│   └── IM00001
└── EXPORT/
    ├── DISK1/
    │   ├── 0001/
    │   │   ├── IM00001
    │   │   ├── IM00002
    │   │   ├── IM00003
    │   │   └── ...
    │   ├── 0002/
    │   │   ├── IM00010
    │   │   ├── IM00011
    │   │   ├── IM00012
    │   │   └── ...
    │   ├── 0003/
    │   │   ├── IM00019
    │   │   ├── IM00020
    │   │   ├── IM00021
    │   │   └── ...
    │   └── 0004/
    │       ├── IM00028
    │       ├── IM00029
    │       └── IM00030
    └── README.TXT
```

## 2. Organized Output Structure / 整理後の出力ツリー

When organized using the default layout (`device-date`), DICOM files are sorted into stable series directories with standardized metadata summaries:

```text
organized/
├── Example-Medical_Demo-CT/
│   └── 20260604/
│       ├── 000001_Axial-CT/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── dicom_parameters.csv
│       └── series_summary.csv
├── Example-Medical_Demo-MR-1.5T/
│   └── 20260603/
│       ├── 000001_T1/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── 000002_T2/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── 000003_FLAIR/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── dicom_parameters.csv
│       └── series_summary.csv
├── Example-Medical_Demo-MR-3T/
│   ├── 20260601/
│   │   ├── 000001_T1/
│   │   │   ├── 000001.dcm
│   │   │   ├── 000002.dcm
│   │   │   └── 000003.dcm
│   │   ├── 000002_T2/
│   │   │   ├── 000001.dcm
│   │   │   ├── 000002.dcm
│   │   │   └── 000003.dcm
│   │   ├── 000003_FLAIR/
│   │   │   ├── 000001.dcm
│   │   │   ├── 000002.dcm
│   │   │   └── 000003.dcm
│   │   ├── 000099_PR/
│   │   │   └── 000001.dcm
│   │   ├── dicom_parameters.csv
│   │   └── series_summary.csv
│   └── 20260602/
│       ├── 000001_T1/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── 000002_T2/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── 000003_FLAIR/
│       │   ├── 000001.dcm
│       │   ├── 000002.dcm
│       │   └── 000003.dcm
│       ├── dicom_parameters.csv
│       └── series_summary.csv
├── all_series_summary.csv
├── file_report.csv
└── organize_summary.json
```

## 3. File Processing Summary / 入力ファイル処理状況の内訳

- Candidate Files / 検出ファイル総数: 33
- Successfully Organized / 整理完了ファイル数: 31
- Unprocessed Files by Reason / 未処理の理由ごとの内訳:
  - `duplicate_identical`: 1 file(s) (`EXPORT/DISK1/0001/IM00001` (duplicate of `BACKUP/IM00001`))
  - `not_dicom`: 1 file(s) (`EXPORT/README.TXT`)

本体は、フォルダ名・ファイル名を並び順にたどって最初に見つけたファイルを整理し、同じ SOPInstanceUID で内容も同じ後のファイルを `duplicate_identical` として記録します。どのファイルの重複かは `file_report.csv` の `DuplicateOf` 列に出ます。
When scanning files in alphabetical order, the first instance found is organized, while subsequent files with identical content and SOPInstanceUID are skipped and recorded as `duplicate_identical`. The `DuplicateOf` column in `file_report.csv` shows which file was duplicated.

## 4. Extracted Imaging Parameters / 抽出された撮像条件の抜粋 (`all_series_summary.csv`)

`all_series_summary.csv` aggregates modality parameters across all studies:

| StudyFolder | SeriesFolder | SeriesDescription | Modality | TR_ms | TE_ms | FlipAngle_deg | ScanDuration |
|---|---|---|---|---|---|---|---|
| Example-Medical_Demo-CT/20260604 | Example-Medical_Demo-CT/20260604/000001_Axial-CT | Demo CT Axial CT | CT | N/A | N/A | N/A | N/A |
| Example-Medical_Demo-MR-1.5T/20260603 | Example-Medical_Demo-MR-1.5T/20260603/000001_T1 | Demo MR 1.5T T1 | MR | 450.0 | 12.0 | 70.0 | 00:01:40 |
| Example-Medical_Demo-MR-1.5T/20260603 | Example-Medical_Demo-MR-1.5T/20260603/000002_T2 | Demo MR 1.5T T2 | MR | 3500.0 | 90.0 | 90.0 | 00:02:40 |
| Example-Medical_Demo-MR-1.5T/20260603 | Example-Medical_Demo-MR-1.5T/20260603/000003_FLAIR | Demo MR 1.5T FLAIR | MR | 8000.0 | 110.0 | 140.0 | 00:03:30 |
| Example-Medical_Demo-MR-3T/20260601 | Example-Medical_Demo-MR-3T/20260601/000001_T1 | Demo MR 3T T1 | MR | 500.0 | 10.0 | 70.0 | 00:02:00 |
| Example-Medical_Demo-MR-3T/20260601 | Example-Medical_Demo-MR-3T/20260601/000002_T2 | Demo MR 3T T2 | MR | 4000.0 | 80.0 | 90.0 | 00:03:00 |
| Example-Medical_Demo-MR-3T/20260601 | Example-Medical_Demo-MR-3T/20260601/000003_FLAIR | Demo MR 3T FLAIR | MR | 9000.0 | 120.0 | 150.0 | 00:04:00 |
| Example-Medical_Demo-MR-3T/20260602 | Example-Medical_Demo-MR-3T/20260602/000001_T1 | Demo MR 3T T1 | MR | 500.0 | 10.0 | 70.0 | 00:02:00 |
| Example-Medical_Demo-MR-3T/20260602 | Example-Medical_Demo-MR-3T/20260602/000002_T2 | Demo MR 3T T2 | MR | 4000.0 | 100.0 | 90.0 | 00:03:00 |
| Example-Medical_Demo-MR-3T/20260602 | Example-Medical_Demo-MR-3T/20260602/000003_FLAIR | Demo MR 3T FLAIR | MR | 9000.0 | 120.0 | 150.0 | 00:04:00 |
