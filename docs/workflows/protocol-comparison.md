# Cross-Scanner Protocol Comparison / 装置間撮像プロトコル比較

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

In clinical research and multi-center trials, ensuring consistent MRI acquisition parameters across different scanners (e.g., Canon, GE, Philips, Siemens) is critical to avoiding sequence bias. This workflow demonstrates how to audit and compare scanning protocols using `dicom-organizer`.

### 1. Generating Unified Parameter Summaries

First, use list-only mode to extract all imaging parameters without duplicating slice data:

```bash
dicom-organizer /path/to/multicenter-study --list-only
```

This creates `all_series_summary.csv` directly under the output root, containing standardized columns for:
- Repetition Time (`TR_ms`), Echo Time (`TE_ms`), Flip Angle (`FlipAngle_deg`)
- Matrix size (`Matrix_RowsxCols`), Field of View (`FOV_HxW_mm`), Slice Thickness (`SliceThickness_mm`)
- In-plane Phase Encoding Direction (`InPlanePhaseEncodingDirection`, `PhaseEncodingDirectionPatient`)
- Parallel Imaging Acceleration Factor (`ParallelReductionFactorInPlane`)
- Scan Duration (`ScanDuration`)

### 2. Comparing in Spreadsheet or Script

#### Option A: Direct Spreadsheet Inspection
Open `all_series_summary.csv` in Excel or LibreOffice Calc. Sort or pivot by `SeriesDescription` or `ProtocolName` to compare parameter columns side-by-side across different `Manufacturer` and `ManufacturerModelName` values.

#### Option B: Automated Script (`examples/compare_protocols.py`)
Run the bundled protocol audit script to group series and flag discrepancies automatically:

```bash
python examples/compare_protocols.py organized_list/all_series_summary.csv
```

When comparing identical scanning protocols across different scanners, grouping by `--by ProtocolName` is recommended because `SeriesDescription` often varies by device or technician convention:

```bash
python examples/compare_protocols.py organized_list/all_series_summary.csv --by ProtocolName
```

The script highlights differences in TR, TE, slice thickness, or matrix dimensions across matching sequence descriptions, enabling rapid quality control before cohort analysis.

---

<a id="japanese"></a>
## 日本語

多施設共同研究や機器更新時において、複数メーカー（Canon、GE、Philips、Siemens）の MRI 装置間で撮像パラメータ（プロトコル）の整合性を確認することは、画質バイアスを防ぐために不可欠です。本ガイドでは、`dicom-organizer` を用いた撮像条件の比較手順を解説します。

### 1. 横断的なパラメータ一覧表の作成

まず、画像ファイルをコピーせずに高速にメタデータを集約できる「一覧のみモード」を実行します:

```bash
dicom-organizer /path/to/multicenter-study --list-only
```

出力ルート直下に `all_series_summary.csv` が生成されます。ここには以下の共通指標が整理されています:
- 繰り返し時間 (`TR_ms`)、エコー時間 (`TE_ms`)、フリップ角 (`FlipAngle_deg`)
- マトリクスサイズ (`Matrix_RowsxCols`)、撮像視野 (`FOV_HxW_mm`)、スライス厚 (`SliceThickness_mm`)
- 位相エンコード方向 (`InPlanePhaseEncodingDirection`、`PhaseEncodingDirectionPatient`)
- パラレルイメージング倍速数 (`ParallelReductionFactorInPlane`)
- 撮像時間 (`ScanDuration`)

### 2. 表計算ソフトまたはスクリプトでの比較

#### 方法 A: 表計算ソフトでの目視確認
`all_series_summary.csv` を Excel 等で開き、`SeriesDescription` や `ProtocolName` で並べ替えやピボット集計を行います。装置（`ManufacturerModelName`）ごとの設定差異を一目で確認できます。

#### 方法 B: 自動比較スクリプトの利用 (`examples/compare_protocols.py`)
リポジトリ同梱の比較スクリプトを実行することで、系列名の一致するシリーズ間のパラメータ差分を自動検出できます:

```bash
python examples/compare_protocols.py organized_list/all_series_summary.csv
```

装置をまたいで同じプロトコルを比較する際は、`SeriesDescription` は装置ごとに文言が異なることが多いため `--by ProtocolName` を指定するのが適しています:

```bash
python examples/compare_protocols.py organized_list/all_series_summary.csv --by ProtocolName
```

TR や TE、スライス厚、FOV の乖離が端末上に一覧表示され、データ解析前の品質管理（QA）を迅速に行えます。
