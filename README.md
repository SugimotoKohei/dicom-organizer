# organize-dicoms

DICOM ファイルを `AcquisitionDate` と `SeriesInstanceUID` 単位で安定したディレクトリ構造に整理するローカルアプリです。
CLI を標準機能として提供し、PySide6 GUI は任意依存として追加できます。

## セットアップ

```bash
uv sync
```

Python は 3.11 系を想定します。

## PC上の通常コマンドとして使う

開発中のこのリポジトリを、PATH 上の `organize-dicoms` としてインストールします。

```bash
uv tool install --editable . --force
organize-dicoms --help
dicom-organizer --help
```

`~/.local/bin` が PATH にないという警告が出た場合は、以下を実行して新しいシェルを開き直してください。

```bash
uv tool update-shell
```

`dicom-organizer` は旧名互換のエイリアスです。
既存の `dicom-organizer` が先に PATH 上で見つかる環境では、主コマンドの `organize-dicoms` を使うか、`~/.local/bin` が既存コマンドより前に来るように PATH を調整してください。

## CLI

```bash
uv run organize-dicoms --input /path/to/dicom-root --force-read --if-exists skip
```

通常はコピーで整理します。元ファイルを移動する場合は、誤操作防止のため `--action move --confirm-move` が必要です。

任意のDICOMタグを `mri_parameters.csv` に追加したい場合は、`--dicom-tag` または `--tag` を複数回指定できます。

```bash
organize-dicoms --input /path/to/dicom-root \
  --dicom-tag EchoTime \
  --dicom-tag 0018,0080 \
  --dicom-tag CustomPhase=(0018,1312)
```

タグは DICOM keyword、`0018,0080`、`(0018,0080)`、`0x00180080` の形式を受け付けます。
列名を指定しない場合は `DICOM_EchoTime` のような列名で出力します。
位相エンコード方向など標準出力に含めないタグも、必要な場合は `--dicom-tag InPlanePhaseEncodingDirection` のように追加できます。

標準の撮像条件として、TR/TE、FOV、matrix、pixel bandwidth、echo train length、flip angle、slice thickness、
NEX、磁場強度、sequence/protocol系情報に加えて、`SequenceName`、`InversionTime_ms`、
`EchoNumbers`、`AcquisitionMatrix`、`NumberOfPhaseEncodingSteps`、`PercentSampling`、
`PercentPhaseFOV`、`SAR` を出力します。

## GUI

GUI を使う場合だけ `gui` extra を入れてください。

```bash
uv tool install --editable '.[gui]' --force
```

```bash
uv run organize-dicoms-gui
```

GUI では入力フォルダと出力フォルダを選び、まず `Dry Run` で Series 一覧を確認してから `Run` します。
`move` または `overwrite` を選んだ場合は実行前に確認ダイアログを出します。

## 出力

既定では `<input>/organized/` に以下を出力します。

```text
organized/<AcquisitionDate>/<SeriesNumber>_<ProtocolName>/
├─ 000001.dcm
├─ ...
organized/<AcquisitionDate>/mri_parameters.csv
organized/<AcquisitionDate>/series_summary.csv
organized/organize_summary.json
```

既定のseriesディレクトリ名は `SeriesNumber_ProtocolName` です。
同じ日付内で同名になる別seriesがある場合は、混在を避けるため先頭から `_01`, `_02` のような連番を付けます。

## 患者情報

既定の `--patient-mode keep` では、`PatientName` と `PatientID` をメタデータCSVに残します。
共有や外部持ち出しをする出力では、以下のどちらかを明示してください。

```bash
organize-dicoms --input /path/to/dicom-root --patient-mode hash
organize-dicoms --input /path/to/dicom-root --patient-mode drop
```

`hash` は `PatientName` / `PatientID` を `sha256:<digest>` 形式に置き換え、`drop` は `"N/A"` にします。
どちらの場合も `PatientNameHash` / `PatientIDHash` は再確認用の短いハッシュとして出力します。

## テスト

```bash
uv run pytest
uv run ruff check
uv build
```
