# Pre-processing for 3D Slicer / 3D Slicer 取り込み前のシリーズ整理

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

[3D Slicer](https://www.slicer.org/) is an open-source platform for medical image visualization and volumetric analysis. Before importing raw DICOM files into Slicer, organizing folders and filtering out non-DICOM files with `dicom-organizer` structures your directory before database import.

### 1. Preparing the Dataset

When exported from optical media or clinical archives, directories often contain deep, uninformative paths, redundant copies, and extraneous non-DICOM files (such as `.txt` or `.jpg`). Note that non-image DICOM objects (such as Presentation States or Structured Reports) are organized into series folders like images.

Organize the target directory first:
```bash
dicom-organizer /path/to/raw-dicom-export
```

This cleans the directory structure, skips duplicate identical files, and sorts files into series directories:
`<Device>/<StudyDate>/<SeriesNumber>_<Label>/000001.dcm` (where the label is derived from ProtocolName, or SeriesDescription for Philips, GE, and Canon/Toshiba).

### 2. Importing into 3D Slicer

According to official 3D Slicer documentation:
1. **Importing Options**:
   - Drag and drop the organized series folder directly into the 3D Slicer application window and confirm **"Load directory in DICOM database"**.
   - Or open the **DICOM** module from the toolbar and click the **Import** button to select the organized folder.
2. **Database Copy Setting**:
   - In the **Import** button dropdown, Slicer provides the option **"Copy imported files to DICOM database"**. Enabling this copies the files into Slicer's internal database (recommended for removable media), while leaving it unchecked records only the file paths.
3. **Browsing Hierarchy**:
   - 3D Slicer displays imported data in a standard **Patient → Study → Series → Instance** hierarchy.
4. **Important Slicer Storage Notes**:
   - Slicer documentation recommends placing its DICOM database on a path containing **ASCII characters only**.
   - Avoid network or cloud storage drives for the active Slicer database.
   - On Windows, ensure path lengths remain under approximately 200 characters.
5. **Exporting**: Slicer can export organized DICOM datasets back out via the Data module (right-click -> export).

---

<a id="japanese"></a>
## 日本語

[3D Slicer](https://www.slicer.org/) は、医用画像の 3 次元可視化やセグメンテーションを行うオープンソースソフトウェアです。Slicer の DICOM データベースに取り込む前に、`dicom-organizer` でフォルダを整理し、非 DICOM ファイル（テキストや画像ファイル等）を仕分けておくことで、体系化されたシリーズ単位で取り込むことができます。

### 1. データの事前準備

光学メディアやコンソールから取り出したデータには、深い入れ子構造、同一スライスの重複コピー、説明テキスト等の非 DICOM ファイルが含まれていることが多くあります。なお、非画像の DICOM（PR や SR 等）は画像と同様にシリーズフォルダに整理されます。

まず `dicom-organizer` でデータを整理します:
```bash
dicom-organizer /path/to/raw-dicom-export
```

これにより、同一内容の重複ファイルが自動でスキップされ、`<装置名>/<検査日>/<シリーズ番号>_<ラベル>/000001.dcm`（ラベルは通常 ProtocolName、Philips・GE・Canon/Toshiba では SeriesDescription）の階層に整理されます。

### 2. 3D Slicer への取り込み手順

3D Slicer の公式ドキュメントに基づく手順です:
1. **取り込み方法**:
   - 整理後のシリーズフォルダを 3D Slicer のウィンドウへ直接ドラッグ＆ドロップし、「Load directory in DICOM database」を選択します。
   - または、モジュール一覧から **DICOM** モジュールを開き、**Import** ボタンから整理後のフォルダを指定します。
2. **データベースへのコピー設定**:
   - Import ボタン横のドロップダウンに「**Copy imported files to DICOM database**」があります。有効にすると Slicer 内部のデータベース領域にファイルをコピーし（外付けメディア等で推奨）、無効にすると元のファイルパスのみを記録します。
3. **ブラウザ表示**:
   - Slicer の DICOM ブラウザには、**Patient → Study → Series → Instance** の階層で整然と表示されます。
4. **Slicer 利用時の注意点**:
   - Slicer の公式ドキュメントでは、データベースの保存先パスは **ASCII（半角英数）文字のみ**で構成することが推奨されています。
   - ネットワークドライブやクラウド同期ドライブ上へのデータベース配置は避けてください。
   - Windows 環境ではパス長が約 200 文字未満になるよう配慮してください。
5. **書き出し**: 取り込んだデータは、Slicer の Data モジュールで右クリックしてエクスポートすることも可能です。
