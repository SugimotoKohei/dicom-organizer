# CLI Usage Guide / コマンドライン利用ガイド

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

`dicom-organizer` provides a comprehensive command-line interface for scanning, sorting, and extracting parameter summaries from local DICOM repositories.

### 1. Basic Invocation

You can run the tool using the installed console script or directly via Python module entry points:

```bash
# Preferred positional command
dicom-organizer /path/to/dicom-root

# Alternative module execution when PATH is not configured
python -m dicom_organizer /path/to/dicom-root
python -m dicom_organizer.cli /path/to/dicom-root

# Check installed version
dicom-organizer --version
```

`-i /path/to/dicom-root` and `--input /path/to/dicom-root` are also accepted for backwards compatibility, but the positional path is preferred. By default, files are copied to `<input>/organized/`. Source files are never modified or removed.

### 2. Operational Modes

#### Dry Run (`-n` / `--dry-run`)
Inspect candidate files, planned series directories, and anticipated metadata outputs without writing any files to disk:
```bash
dicom-organizer /path/to/dicom-root -n
```

#### List-Only Mode (`--list-only`)
When you only need imaging parameter tables (`all_series_summary.csv`, `all_dicom_parameters.csv`) and file status reports (`file_report.csv`, `organize_summary.json`) without copying gigabytes of slice files:
```bash
dicom-organizer /path/to/dicom-root --list-only
```
By default, list-only outputs are written to `<input>/organized_list/`. Per-study `dicom_parameters.csv` tables are not generated in list-only mode.

#### Resuming and Existing Files (`--if-exists`)
Existing output files raise an error by default to prevent accidental overwrite. When resuming an interrupted run or appending new studies into an existing output directory, use `--if-exists skip`:
```bash
dicom-organizer /path/to/dicom-root --if-exists skip
```
When re-running with `--if-exists skip`, metadata CSVs are reconstructed across the entire output directory including previously organized series, whereas `organize_summary.json` records the log for that specific run.

#### Checksum Verification (`--checksum`)
Compute and verify SHA-256 digests for all copied files:
```bash
dicom-organizer /path/to/dicom-root --checksum
```

#### Self-Test and Environment Diagnostics
Validate your installation using built-in synthetic datasets:
```bash
dicom-organizer --self-test
dicom-organizer --self-test --self-test-report ~/Desktop/self-test.txt
```
To print sanitized diagnostic information for bug reporting:
```bash
dicom-organizer --diagnostics
```

### 3. Metadata Profiles (`-p` / `--profile`)

The default metadata profile is `auto`, which writes a single `dicom_parameters.csv` for supported image modalities (`MR`, `CT`, `US`, `XA`, `PT`) and dynamically expands columns based on the modalities actually present in the dataset.

- `--profile auto`: Union of columns for present modalities (default).
- `--profile generic`: Common parameters only (dates, scanner, patient identifiers).
- `--profile mr`: Specialized MRI columns (TR, TE, flip angle, bandwidth, echo spacing, coils, acceleration).
- `--profile ct`: Specialized CT columns (kVp, tube current, exposure time, slice thickness).
- `--profile us`: Ultrasound columns (transducer type, thermal indices).
- `--profile xa`: X-Ray Angiography columns (KVP, distance source to detector).
- `--profile pt`: Positron Emission Tomography columns (radiopharmaceutical info).

```bash
dicom-organizer /path/to/dicom-root -p generic
dicom-organizer /path/to/dicom-root -p ct
```

`dicom_parameters.csv` and `series_summary.csv` focus on supported image objects. Presentation states and vendor-private helper objects may still be organized into folders, but they are excluded from these parameter tables.

### 4. Folder Layouts (`--layout`)

Choose how organized directories are structured:
- `device-date` (default): `<Device>/<StudyDate>/<SeriesNumber>_<SeriesFolderLabel>/`
- `study`: `<StudyDate>_<StudyKey>/<SeriesNumber>_<SeriesFolderLabel>/`
- `patient-study`: `<PatientKey>/<StudyDate>_<StudyKey>/<SeriesNumber>_<SeriesFolderLabel>/`

The date used for folder hierarchy is `StudyDate` (while `AcquisitionDate` remains available as a CSV column); missing or invalid dates fall back to `unknown_date`.

The default series folder name uses a normalized series label: usually `ProtocolName`, but on vendors where `SeriesDescription` better matches the console-visible sequence name (for example Philips, GE, and Canon/Toshiba-family systems), it prefers `SeriesDescription`. If a Philips series contains multiple reconstruction types in the same `SeriesInstanceUID`, the default folder name also appends a reconstruction label derived from `ImageType`. When a Philips series label is only a number, the default name also prefixes the descriptive anchor label from the same acquisition when one is available.

### 5. Header Handling and Privacy

- **Header Reading (`--no-force-read`)**: By default, DICOM headers are read with `force=True` so exports with slightly non-standard headers are still included. Add `--no-force-read` if you want to require standard DICOM preamble headers.
- **Privacy Modes (`--patient-mode`)**:
  - `--patient-mode keep` (default): writes plaintext `PatientName` and `PatientID` along with their 16-character SHA-256 digests in `PatientNameHash` and `PatientIDHash`.
  - `--patient-mode hash`: writes `sha256:`-prefixed 16-character SHA-256 hex digests (e.g. `sha256:e3b0c44298fc1c14`) into `PatientName` and `PatientID`, and the digest strings into `PatientNameHash` and `PatientIDHash`.
  - `--patient-mode drop`: strictly writes `N/A` for all four patient identifier and hash columns.
- **Custom DICOM Tags (`-t` / `--dicom-tag`)**: Append any standard or private DICOM element to CSV outputs:
  ```bash
  dicom-organizer /path/to/dicom-root -t EchoTime -t TransmitCoilName
  ```

### 6. Institutional Configuration File (`--config`)

Load default settings from a TOML configuration file:
```bash
dicom-organizer /path/to/dicom-root --config /etc/dicom-organizer/config.toml
```
Or export the current effective configuration:
```bash
dicom-organizer --print-config
```

### 7. Specialized Parameter Derivations

#### Phase Encoding Direction
MR outputs include `InPlanePhaseEncodingDirection` and the derived `PhaseEncodingDirectionPatient` in both `dicom_parameters.csv` and `series_summary.csv`. The derived value maps the DICOM `ROW`/`COL` image axis through `ImageOrientationPatient` and writes the positive image-index direction as a patient-relative arrow such as `R→L`, `A→P`, or `H→F`. `PatientPosition` is also retained in both CSV files for reference, but is not used as a geometric transform because DICOM defines it as an annotation. Missing or unsupported source geometry produces `N/A`.

#### Parallel Imaging Acceleration Factor
The MR column `ParallelReductionFactorInPlane` reports the standard DICOM in-plane parallel-imaging acceleration factor in both CSV files. For example, `2.0` means a twofold measurement-time reduction factor. Classic top-level and Enhanced MR functional-group values are supported. For Siemens DICOM without the standard attribute, the explicit CSA protocol value `sPat.lAccelFactPE` is used as a fallback. If neither value exists, the result is `N/A`.

### 8. Desktop GUI Launcher (macOS)

For users who installed `dicom-organizer[gui]`, generate a standalone launcher bundle:
```bash
dicom-organizer-gui-app
open ~/Applications/dicom-organizer.app
```

---

<a id="japanese"></a>
## 日本語

`dicom-organizer` は、手元の散らばった DICOM フォルダの走査、階層整理、および撮像パラメータの一覧抽出を行う充実したコマンドライン機能を提供します。

### 1. 基本的な実行方法

インストール済みのコマンド、または Python モジュール経由で実行できます:

```bash
# 基本の実行（位置引数で入力フォルダを指定）
dicom-organizer /path/to/dicom-root

# PATH が通っていない環境でのモジュール実行
python -m dicom_organizer /path/to/dicom-root
python -m dicom_organizer.cli /path/to/dicom-root

# バージョンの確認
dicom-organizer --version
```

互換性のため `-i /path/to/dicom-root` や `--input /path/to/dicom-root` も受け付けますが、通常は位置引数を推奨します。既定では `<input>/organized/` にファイルがコピーされます。元ファイルが変更・削除されることはありません。

### 2. 実行モードの選択

#### 事前確認（dry-run: `-n` / `--dry-run`）
ファイルの書き込みを行わず、処理対象ファイル、作成予定のフォルダ階層、出力メタデータを画面上で確認します:
```bash
dicom-organizer /path/to/dicom-root -n
```

#### 一覧のみモード（`--list-only`）
巨大な画像ファイルをコピーせず、撮像パラメータ表（`all_series_summary.csv`、`all_dicom_parameters.csv`）と処理状況レポート（`file_report.csv`、`organize_summary.json`）だけを作成したい場合に使用します:
```bash
dicom-organizer /path/to/dicom-root --list-only
```
既定では `<input>/organized_list/` に出力されます。一覧のみモードでは検査フォルダごとの `dicom_parameters.csv` は作成されません。

#### 中断後の再開と既存フォルダへの追記（`--if-exists`）
誤った上書きを防ぐため、出力先にファイルが存在する場合は既定でエラーとなります。中断した処理を再開する場合や、新しい検査を追加する場合は `--if-exists skip` を指定します:
```bash
dicom-organizer /path/to/dicom-root --if-exists skip
```
`--if-exists skip` で再実行した場合、既存の出力シリーズを含めた出力ディレクトリ全体でメタデータ CSV が再構築されます。一方、`organize_summary.json` はその実行単体のログを記録します。

#### チェックサム検証（`--checksum`）
コピーされたすべてのファイルに対して SHA-256 ハッシュを計算・検証し、データの整合性を担保します:
```bash
dicom-organizer /path/to/dicom-root --checksum
```

#### 自己診断と環境情報出力
内蔵の合成データセットを用いてツールの動作を確認できます:
```bash
dicom-organizer --self-test
dicom-organizer --self-test --self-test-report ~/Desktop/self-test.txt
```
不具合報告用に、個人情報をマスクした環境情報を出力します:
```bash
dicom-organizer --diagnostics
```

### 3. メタデータプロファイル (`-p` / `--profile`)

既定のプロファイルは `auto` で、対応モダリティ（`MR`, `CT`, `US`, `XA`, `PT`）の画像を 1 つの `dicom_parameters.csv` にまとめ、データセット内に実際に含まれるモダリティに応じて列を動的に展開します。

- `--profile auto`: 検出された全モダリティの統合列（既定値）。
- `--profile generic`: 共通列のみ（日時、装置、患者識別子）。
- `--profile mr`: MR 固有列（TR, TE, フリップ角, ピクセル帯域, エコー間隔, 受信コイル, 加速係数など）。
- `--profile ct`: CT 固有列（管電圧, 管電流, 照射時間, スライス厚など）。
- `--profile us`: 超音波固有列（プローブ情報, サーマルインデックスなど）。
- `--profile xa`: 血管造影固有列（管電圧, 検出器間距離など）。
- `--profile pt`: PET 固有列（放射性薬剤情報など）。

```bash
dicom-organizer /path/to/dicom-root -p generic
dicom-organizer /path/to/dicom-root -p ct
```

`dicom_parameters.csv` と `series_summary.csv` は対応している画像オブジェクトを対象にしています。プレゼンテーションステートやベンダー独自の補助オブジェクトもフォルダ整理はされますが、パラメータ表からは除外されます。

### 4. フォルダレイアウトの指定 (`--layout`)

整理後のフォルダ構造を選択できます:
- `device-date`（既定値）: `<Device>/<StudyDate>/<SeriesNumber>_<SeriesFolderLabel>/`
- `study`: `<StudyDate>_<StudyKey>/<SeriesNumber>_<SeriesFolderLabel>/`
- `patient-study`: `<PatientKey>/<StudyDate>_<StudyKey>/<SeriesNumber>_<SeriesFolderLabel>/`

フォルダ階層の日付には `StudyDate` を採用しています（`AcquisitionDate` は CSV 列として残ります）。日付が不正または欠損している場合は `unknown_date` になります。

シリーズフォルダ名の既定値は正規化した series label で、通常は `ProtocolName`、ただし Philips や GE、Canon/Toshiba 系のように `SeriesDescription` のほうがコンソール上の系列名に近い装置では `SeriesDescription` を優先します。さらに、Philips で同じ `SeriesInstanceUID` に複数の再構成が含まれる場合は、`ImageType` 由来の再構成ラベルもフォルダ名に付きます。また、Philips でラベルが数字だけの系列は、同一 acquisition 内の説明的な系列名を前置して分かりやすくします。

### 5. ヘッダーの読み取りとプライバシー設定

- **ヘッダー読み取り (`--no-force-read`)**: 既定では `force=True` で DICOM ヘッダーを読み、少し非標準なエクスポート由来のファイルも対象にします。標準的な DICOM ヘッダーのみを対象としたい場合は `--no-force-read` を指定します。
- **プライバシー設定 (`--patient-mode`)**:
  - `--patient-mode keep`（既定値）: `PatientName` と `PatientID` をそのまま出力し、`PatientNameHash` と `PatientIDHash` に 16 文字の SHA-256 ハッシュ値を出力します。
  - `--patient-mode hash`: `PatientName` と `PatientID` に `sha256:` 接頭辞付きの 16 文字ハッシュ値（例: `sha256:e3b0c44298fc1c14`）を出力し、ハッシュ列にも同じ値を出力します。
  - `--patient-mode drop`: 患者氏名、ID、および各ハッシュ列をすべて `N/A` で出力します。
- **追加タグの出力 (`-t` / `--dicom-tag`)**: 任意の DICOM タグを CSV に追加します:
  ```bash
  dicom-organizer /path/to/dicom-root -t EchoTime -t TransmitCoilName
  ```

### 6. 施設共通設定ファイル (`--config`)

TOML 形式の設定ファイルから既定値を読み込みます:
```bash
dicom-organizer /path/to/dicom-root --config /etc/dicom-organizer/config.toml
```
現在の有効な設定を TOML 形式で出力することもできます:
```bash
dicom-organizer --print-config
```

### 7. 専門的なパラメータの導出ロジック

#### 位相エンコード方向の患者座標写像
MR 出力では、`InPlanePhaseEncodingDirection` と、そこから導出した `PhaseEncodingDirectionPatient` を `dicom_parameters.csv` と `series_summary.csv` の両方に出力します。導出列は DICOM の `ROW` / `COL` 軸を `ImageOrientationPatient` で患者座標へ写像し、画像 index が増える向きを `R→L`、`A→P`、`H→F` などの矢印で表します。参照用の `PatientPosition` も両 CSV に残しますが、DICOM 上は注釈情報なので幾何変換には使いません。必要な geometry が欠損または非対応の場合は `N/A` になります。

#### パラレルイメージング倍速数
MR 列の `ParallelReductionFactorInPlane` には、標準 DICOM の面内パラレルイメージング倍速数を両 CSV へ出力します。たとえば `2.0` は測定時間の短縮係数が 2 倍であることを表します。classic DICOM の top-level 属性と Enhanced MR の functional group に対応します。標準属性がない Siemens DICOM では、CSA protocol の明示値 `sPat.lAccelFactPE` を fallback として使います。どちらもない場合は `N/A` です。

### 8. macOS 用デスクトップランチャー

`dicom-organizer[gui]` をインストールした環境で、Spotlight や Dock から直接起動できるランチャーを作成できます:
```bash
dicom-organizer-gui-app
open ~/Applications/dicom-organizer.app
```
