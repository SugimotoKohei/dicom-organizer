# Storing Organized Series in Orthanc / 整理後ファイルの Orthanc 登録連携

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

[Orthanc](https://www.orthanc-server.com/) is a lightweight, open-source DICOM server running on Windows, Linux, and macOS with a built-in REST API. While `dicom-organizer` intentionally avoids network PACS communication, it can be used to organize raw files locally before uploading them to an Orthanc research server.

### 1. Organizing Files Prior to Storing

Before loading disorganized files into a local PACS, organize and inspect them with `dicom-organizer`:
```bash
dicom-organizer /path/to/raw-inbox -o /path/to/clean-staging
```

This ensures identical duplicate files are not copied into the organized tree, and series metadata is indexed in `all_series_summary.csv`.

### 2. Uploading via Orthanc Explorer (Web Interface)

According to official Orthanc documentation:
1. Open the Orthanc Explorer web interface in your browser:
   `http://localhost:8042/app/explorer.html#upload` (port may vary based on configuration).
2. Drag and drop the organized DICOM files or series folders into the upload drop area.
3. Click the **Upload** button to store the series into the Orthanc archive.

### 3. Sending via DICOM Network Protocol (DCMTK `storescu`)

According to official Orthanc documentation, you can transmit files via the standard DICOM network protocol using DCMTK's `storescu` utility. Because `.dcm` files are placed inside individual series directories, navigate into the desired series folder before running `storescu`:

```bash
cd /path/to/clean-staging/Example-Medical_Demo-MR-3T/20260601/000002_T2
storescu -aec ORTHANC localhost 4242 *.dcm
```

This routes the organized slice files directly to the Orthanc DICOM listener (AET: `ORTHANC`, default DICOM port 4242).

---

<a id="japanese"></a>
## 日本語

[Orthanc](https://www.orthanc-server.com/) は、Windows、Linux、macOS で動作するオープンソースの軽量 DICOM サーバー（ミニ PACS）であり、REST API を備えています。`dicom-organizer` 自体はネットワーク通信機能を持たない設計となっていますが、Orthanc に取り込む前のローカル整理ツールとして利用できます。

### 1. Orthanc 登録前のデータ整理

未整理のファイル群を一括で登録する前に、`dicom-organizer` でフォルダを整理します:
```bash
dicom-organizer /path/to/raw-inbox -o /path/to/clean-staging
```

同一内容の重複ファイルはコピーされず、整理されたシリーズ単位で登録作業を進めることができます。

### 2. Orthanc Explorer（Web 画面）からのアップロード

Orthanc の公式ドキュメントに基づく手順です:
1. Web ブラウザで Orthanc Explorer のアップロード画面を開きます:
   `http://localhost:8042/app/explorer.html#upload`（ポート番号は設定により異なります）。
2. 整理後の DICOM ファイルまたはシリーズフォルダをアップロード領域にドラッグ＆ドロップします。
3. **Upload** ボタンをクリックすると、Orthanc への登録が完了します。

### 3. DICOM ネットワーク送信（DCMTK `storescu`）

Orthanc 公式ドキュメント記載の DCMTK `storescu` を用いて、DICOM 通信プロトコルで直接送信することも可能です。`.dcm` ファイルはシリーズフォルダ内に配置されるため、送信したいシリーズのフォルダへ移動してからコマンドを実行します:

```bash
cd /path/to/clean-staging/Example-Medical_Demo-MR-3T/20260601/000002_T2
storescu -aec ORTHANC localhost 4242 *.dcm
```

シリーズフォルダ内で上記コマンドを実行することで、Orthanc の DICOM リスナー（AET: `ORTHANC`、既定ポート 4242）へ直接転送できます。
