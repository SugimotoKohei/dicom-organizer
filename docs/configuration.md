# Facility Configuration (TOML)

This document describes how to configure `dicom-organizer` using TOML configuration files.

## Purpose

When organizing DICOM datasets within a hospital, laboratory, or research team, ensuring consistent and reproducible directory structures, metadata extraction profiles, and privacy settings is essential. Configuration files allow teams to standardize and distribute shared organizer settings without requiring users to type long command-line options repeatedly.

## Specifying Configuration Files

You can specify a configuration file in two ways:

1. **Command-line argument**:
   ```bash
   dicom-organizer <INPUT> --config /path/to/facility_config.toml
   ```
2. **Environment variable**:
   Set `DICOM_ORGANIZER_CONFIG` to the file path:
   ```bash
   export DICOM_ORGANIZER_CONFIG=/path/to/facility_config.toml
   dicom-organizer <INPUT>
   ```

Tilde expansion (`~`) is supported for configuration file paths specified via `--config` or `DICOM_ORGANIZER_CONFIG`.

If neither is provided, built-in defaults are used. If `--config` or the environment variable points to a file that does not exist or has syntax errors, `dicom-organizer` stops with an error.

## Precedence

Configuration values are resolved using the following order of precedence:

1. **Explicit command-line arguments** (highest priority)
2. **Configuration file values**
3. **Built-in default values** (lowest priority)

For example, if your configuration file specifies `patient_mode = "hash"` and you run with `--patient-mode drop`, `drop` is applied.
For `dicom_tags`, any tags passed via `-t/--tag` on the command line are appended after the tags specified in the configuration file.

## Generating Configuration Templates (`--print-config`)

You can inspect the current effective configuration (defaults + config file + CLI overrides) in TOML format using `--print-config`:

```bash
dicom-organizer --print-config --patient-mode hash --layout study
```

This command does not require an `INPUT` directory and outputs valid TOML to standard output. You can redirect it to a file to create a starter configuration:

```bash
dicom-organizer --print-config > facility_config.toml
```

## Configuration Keys and Types

All configuration keys are optional. Only the following 16 keys are permitted in the configuration file:

| Key | Type | Description / Allowed Values |
|---|---|---|
| `output` | string | Output directory path. Tilde (`~`) is expanded to the user's home directory. Relative paths are resolved relative to the directory containing the config file. |
| `action` | string | File placement action: `"copy"`, `"symlink"`, `"hardlink"`, or `"move"`. |
| `if_exists` | string | Conflict behavior: `"error"`, `"skip"`, `"overwrite"`, or `"rename"`. |
| `profile` | string | Metadata profile: `"auto"`, `"generic"`, `"mr"`, `"ct"`, `"us"`, `"xa"`, or `"pt"`. |
| `patient_mode` | string | Patient identifier handling: `"keep"`, `"hash"`, or `"drop"`. |
| `layout` | string | Folder layout preset: `"device-date"`, `"study"`, or `"patient-study"`. |
| `list_only` | boolean | If `true`, plans organization and generates metadata tables without creating DICOM files. |
| `dicom_tags` | array of strings | Additional DICOM tags to include in CSV tables (e.g. `["EchoTime", "FlipAngle"]`). |
| `force_read` | boolean | If `true`, enables pydicom `force=True`. |
| `include_hidden` | boolean | If `true`, scans hidden files and directories. |
| `include_organized` | boolean | If `true`, does not skip directories named `organized`. |
| `series_dir_template` | string | Series folder name format string (e.g. `"{series_number}_{series_folder_label}"`). |
| `file_template` | string | Output DICOM filename format string (e.g. `"{instance_number_6}.dcm"`). |
| `checksum` | boolean | If `true`, computes and verifies SHA-256 digests during file materialization. |
| `space_check` | boolean | If `true`, performs disk space pre-check before writing files. |
| `progress` | boolean | If `true`, displays console progress bars. |

> [!WARNING]
> Keys that represent ephemeral execution options (such as `input`, `dry_run`, `limit`, `verbose`, and `confirm_move`) are intentionally not allowed in configuration files and will raise a `ValueError`.

## Example

```toml
# facility_config.toml
output = "organized_data"
action = "copy"
if_exists = "error"
profile = "auto"
patient_mode = "hash"
layout = "study"
list_only = false
dicom_tags = ["EchoTime", "FlipAngle"]
force_read = true
checksum = true
space_check = true
```

---

## 日本語

この文書は `dicom-organizer` の TOML 設定ファイル（施設・チーム共通設定）の使い方を説明します。

## 目的

病院・検査室・研究チームで DICOM データを整理する際、出力フォルダ構造や撮像パラメータ抽出項目、患者情報の保護設定をチーム全体で統一・再現可能にすることが不可欠です。設定ファイル（TOML 形式）を配布・共有することで、利用者が毎回長いコマンドラインオプションを指定する手間を省き、均一な整理運用を実現できます。

## 設定ファイルの指定方法

設定ファイルは以下のいずれかの方法で指定します:

1. **コマンドライン引数**:
   ```bash
   dicom-organizer <INPUT> --config /path/to/facility_config.toml
   ```
2. **環境変数**:
   環境変数 `DICOM_ORGANIZER_CONFIG` にファイルパスを設定します:
   ```bash
   export DICOM_ORGANIZER_CONFIG=/path/to/facility_config.toml
   dicom-organizer <INPUT>
   ```

`--config` や `DICOM_ORGANIZER_CONFIG` に指定するパスでは、ホームディレクトリを表すチルダ（`~`）が使用可能です。

いずれも指定されていない場合は、組み込みの既定値が使用されます。指定されたファイルが存在しない場合や TOML 構文に誤りがある場合はエラーとなり停止します。

## 優先順位

各設定項目の値は、以下の優先順位で決定されます:

1. **CLI で明示した引数**（最優先）
2. **設定ファイルの値**
3. **組み込みの既定値**（最低優先）

例えば、設定ファイルで `patient_mode = "hash"` と指定されていても、コマンドラインで `--patient-mode drop` を指定した場合は `drop` が適用されます。
なお、`dicom_tags` については、CLI の `-t/--tag` で指定したタグが設定ファイルの配列の後ろに追加（マージ）されます。

## 雛形（テンプレート）の作成 (`--print-config`)

現在の有効な設定（既定値 + 設定ファイル + コマンドライン指定）を TOML 形式で標準出力に出力できます:

```bash
dicom-organizer --print-config --patient-mode hash --layout study
```

このコマンドは `INPUT` ディレクトリを必要とせず、有効な TOML を標準出力に書き出して終了コード 0 で完了します。リダイレクトして配布用設定ファイルの雛形を作成できます:

```bash
dicom-organizer --print-config > facility_config.toml
```

## 設定キーと型の一覧

設定キーはすべて任意指定です。以下の 16 個のキーのみが設定ファイルで使用可能です:

| キー | 型 | 説明 / 選択肢 |
|---|---|---|
| `output` | 文字列 | 出力先ディレクトリ。チルダ（`~`）はホームディレクトリに展開されます。相対パスで指定した場合、設定ファイルが存在するディレクトリ基準で絶対パス化されます。 |
| `action` | 文字列 | ファイル配置方法: `"copy"`, `"symlink"`, `"hardlink"`, `"move"`。 |
| `if_exists` | 文字列 | 既存ファイル衝突時の挙動: `"error"`, `"skip"`, `"overwrite"`, `"rename"`。 |
| `profile` | 文字列 | メタデータプロファイル: `"auto"`, `"generic"`, `"mr"`, `"ct"`, `"us"`, `"xa"`, `"pt"`。 |
| `patient_mode` | 文字列 | 患者識別子の扱い: `"keep"`, `"hash"`, `"drop"`。 |
| `layout` | 文字列 | 出力フォルダレイアウト: `"device-date"`, `"study"`, `"patient-study"`。 |
| `list_only` | 真偽値 | `true` の場合、DICOM を配置せずメタデータ集計表のみ出力。 |
| `dicom_tags` | 文字列の配列 | CSV に追加する DICOM タグ名またはタグ番号の配列（例: `["EchoTime", "FlipAngle"]`）。 |
| `force_read` | 真偽値 | `true` の場合、pydicom の `force=True` を有効化。 |
| `include_hidden` | 真偽値 | `true` の場合、隠しファイル・フォルダも走査。 |
| `include_organized` | 真偽値 | `true` の場合、`organized` という名前のフォルダも走査対象に含める。 |
| `series_dir_template` | 文字列 | シリーズフォルダ名の書式テンプレート。 |
| `file_template` | 文字列 | 出力 DICOM ファイル名の書式テンプレート。 |
| `checksum` | 真偽値 | `true` の場合、ファイル配置時に SHA-256 チェックサムを計算・検証。 |
| `space_check` | 真偽値 | `true` の場合、配置前に空き容量の事前チェックを実施。 |
| `progress` | 真偽値 | `true` の場合、進捗表示を有効化。 |

> [!WARNING]
> 一時的な実行パラメータ（`input`, `dry_run`, `limit`, `verbose`, `confirm_move` など）は設定ファイルには記述できません。記述された場合は `ValueError` となります。

## 設定ファイルの例

```toml
# facility_config.toml
output = "organized_data"
action = "copy"
if_exists = "error"
profile = "auto"
patient_mode = "hash"
layout = "study"
list_only = false
dicom_tags = ["EchoTime", "FlipAngle"]
force_read = true
checksum = true
space_check = true
```
