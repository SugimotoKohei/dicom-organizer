# Installation and Setup Guide / インストールとセットアップ手順

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

This guide provides instructions for installing, running, updating, and uninstalling `dicom-organizer` for both individual clinical/research users and institutional IT administrators.

### 1. Which Edition Should You Choose?

- **Standalone Desktop App (Recommended for most users)**:
  - **No Python required**. Completely self-contained.
  - Recommended for users who want a graphical desktop tool to organize DICOM folders and inspect series conditions without touching terminal commands.
- **Python Package (CLI and Python GUI)**:
  - Requires Python 3.11 or later and [uv](https://docs.astral.sh/uv/) (or pip). Automated test suite verifies 3.11, 3.12, 3.13, and 3.14. Using the GUI extra follows PySide6 version support (as of 2026-09, PySide6 6.11.1 supports >=3.10,<3.15).
  - Recommended for pipeline integration, automated scripts, headless server environments, or users comfortable with terminal commands.

### 2. Standalone Desktop App Installation

#### Downloading
1. Download the archive for your operating system and architecture from the [GitHub Releases](https://github.com/SugimotoKohei/dicom-organizer/releases) page:
   - macOS (Apple Silicon): `dicom-organizer-<version>-macos-arm64.zip`
   - macOS (Intel): `dicom-organizer-<version>-macos-x86_64.zip`
   - Windows: `dicom-organizer-<version>-windows-x64.zip`
2. Optional: Verify integrity with `SHA256SUMS.txt`:
   ```bash
   # macOS
   shasum -a 256 -c SHA256SUMS.txt
   # Windows (PowerShell) - check the hash and compare the output with SHA256SUMS.txt:
   Get-FileHash dicom-organizer-*.zip -Algorithm SHA256
   Get-Content SHA256SUMS.txt
   ```

#### Unpacking and Running
- **Administrator Privileges**: Not required. The app can be extracted and run from any user directory (e.g., your Desktop, Downloads, or `Applications` / `AppData`).
- **Network Access**: None. The standalone app does not connect to the Internet, does not perform automatic updates, and does not collect or transmit telemetry.

#### First-Launch Security Warnings (Unsigned Binaries)
Formal code signing and notarization certificates have not yet been acquired (planned for future releases). Consequently, modern operating systems will show a security warning upon first launch:

- **macOS**:
  1. When opening the app for the first time, macOS may block it because it is not signed by an identified developer (depending on your macOS version, the warning message may say `"dicom-organizer" cannot be opened because the developer cannot be verified` or `Apple cannot check "dicom-organizer" for malicious software`). Click **Done** or **Cancel**.
  2. Open **System Settings** -> **Privacy & Security**.
  3. Scroll down to the **Security** section where a notice indicates `"dicom-organizer" was blocked from use`.
  4. Click **Open Anyway** (このまま開く). You may be prompted to enter your user login password (administrator rights are not required). Confirm **Open** when prompted. This procedure is only needed once.
- **Windows**:
  1. If Windows SmartScreen displays `Windows protected your PC`, click **More info** (詳細情報).
  2. Click **Run anyway** (実行). This prompt appears only once.

#### Post-Installation Verification
- Open the application and choose **Help** -> **Run Self-Test...** (ヘルプ → 動作確認（自己診断）を実行) from the menu bar.
- Or run self-tests directly from a terminal using the executable path and save a report:
  - macOS:
    ```bash
    /Applications/dicom-organizer.app/Contents/MacOS/dicom-organizer --self-test --self-test-report ~/Desktop/dicom-organizer-self-test.txt
    ```
  - Windows:
    - **PowerShell** (Default terminal in Windows 11):
      ```powershell
      .\dicom-organizer.exe --self-test --self-test-report $env:USERPROFILE\Desktop\dicom-organizer-self-test.txt
      ```
    - **Command Prompt (cmd.exe)**:
      ```cmd
      dicom-organizer.exe --self-test --self-test-report %USERPROFILE%\Desktop\dicom-organizer-self-test.txt
      ```
    (Note: On Windows, the windowed executable may not output directly to the console; open the generated report file to confirm all checks display `[PASS]`.)

#### Offline Environments
To install on an air-gapped machine:
- Copy the standalone `.zip` archive via an approved removable drive (USB, CD/DVD).
- Extract and launch directly. No external dependencies or network downloads are needed.

#### Updating and Downgrading
- **Update**: Download the newer `.zip` release, extract it, and replace the existing application. Your settings (remembered paths, profile choices) will be preserved.
- **Downgrade**: If an issue occurs with a new version, delete the current app and download any previous release `.zip` from GitHub Releases.

#### Uninstalling
1. Delete the application bundle or directory:
   - macOS: Move `dicom-organizer.app` to the Trash.
   - Windows: Delete the `dicom-organizer` directory.
2. Remove saved preferences (optional):
   - macOS: `~/Library/Preferences/com.dicom-organizer.dicom-organizer.plist`
   - Windows (Registry): `HKEY_CURRENT_USER\Software\dicom-organizer\dicom-organizer`
   - Linux: `~/.config/dicom-organizer/dicom-organizer.conf`

---

### 3. Python Package Installation (CLI and Python GUI)

The Python edition requires Python 3.11 or later (automated test suite verifies 3.11, 3.12, 3.13, and 3.14; using the GUI extra follows PySide6 version support, which is Python >=3.10,<3.15 as of PySide6 6.11.1 in 2026-09). Using `uv` is strongly recommended.

#### Installing with uv
- CLI only:
  ```bash
  uv tool install dicom-organizer
  ```
- CLI + PySide6 GUI:
  ```bash
  uv tool install 'dicom-organizer[gui]'
  ```
- Specifying an exact version:
  ```bash
  uv tool install 'dicom-organizer[gui]==0.2.0'
  ```

#### Updating and Uninstalling
- Update to the latest version:
  ```bash
  uv tool upgrade dicom-organizer
  ```
- Uninstall:
  ```bash
  uv tool uninstall dicom-organizer
  ```

#### macOS Lightweight Launcher Note
The `dicom-organizer-gui-app` command creates a lightweight macOS application launcher in `~/Applications/` that points to your existing Python environment. Note that `dicom-organizer-gui-app` is intended specifically for users of the Python edition; users who download the Standalone Desktop App should use the standalone `dicom-organizer.app` directly.

#### Offline Installation for Python Edition
Because platform-specific wheels (especially PySide6) differ across operating systems and CPU architectures, wheels must be collected on an online computer with the **same OS and CPU architecture** as the target machine:
```bash
python3 -m pip download --dest ./wheelhouse "dicom-organizer[gui]"
```
Transfer the `./wheelhouse` directory to the offline machine, then install using `--no-index`:
```bash
uv tool install --no-index --find-links ./wheelhouse 'dicom-organizer[gui]'
```

---

<a id="japanese"></a>
## 日本語

本書は、一般の医療従事者・研究者および施設のIT管理者向けに、`dicom-organizer` の導入、起動、更新、旧版への復帰、アンインストール手順を説明します。

### 1. エディションの選択

- **単体アプリ版（推奨）**:
  - **Pythonの事前インストールは一切不要**です。必要なランタイムがすべて同梱されています。
  - コマンドラインを使わず、手元のDICOMフォルダを整理し撮像条件を一覧化したい一般の利用者におすすめです。
- **Pythonパッケージ版（CLIおよびPython GUI）**:
  - Python 3.11 以上と `uv`（または pip）が必要です。自動テストで確認しているのは 3.11・3.12・3.13・3.14 です。GUI を使う場合は PySide6 の対応範囲に従います（2026-09 時点の PySide6 6.11.1 は 3.10 以上 3.15 未満）。
  - バッチ処理や他ツールとの連携スクリプト、サーバ環境での自動化を行う方向けです。

### 2. 単体アプリ版のインストールと起動

#### 入手方法
1. [GitHub Releases](https://github.com/SugimotoKohei/dicom-organizer/releases) からお使いのOS・CPUに合った zip アーカイブをダウンロードします:
   - macOS (Apple Silicon: M1/M2/M3/M4等): `dicom-organizer-<version>-macos-arm64.zip`
   - macOS (Intel): `dicom-organizer-<version>-macos-x86_64.zip`
   - Windows (64ビット): `dicom-organizer-<version>-windows-x64.zip`
2. （任意）`SHA256SUMS.txt` を用いてハッシュ値の一致を確認できます:
   ```bash
   # macOS
   shasum -a 256 -c SHA256SUMS.txt
   # Windows (PowerShell) - ハッシュ値を計算し SHA256SUMS.txt の記載内容と見比べます:
   Get-FileHash dicom-organizer-*.zip -Algorithm SHA256
   Get-Content SHA256SUMS.txt
   ```

#### 展開と起動
- **管理者権限は不要**: インストーラ（setup.exe 等）によるシステム領域への書き込みは行いません。ユーザーのデスクトップやダウンロードフォルダなど、書き込み権限のある任意の場所に展開してそのまま起動できます。
- **ネットワーク通信は行わない**: アプリ起動中および処理中にインターネット通信は一切行いません。自動更新機能や利用状況の外部送信（テレメトリ）もありません。

#### 初回起動時の警告と開き方（未署名アプリの実行）
現在、公的なコード署名証明書（Apple Developer / Windows Authenticode）は未取得であり、将来のバージョンで対応予定です。そのため、初回起動時にOSのセキュリティ機構が警告を表示します。

- **macOS の場合**:
  1. 初回起動時、macOS のバージョンにより「開発元を確認できないため開けません」または「Apple は "dicom-organizer" にマルウェアが含まれていないことを検証できませんでした」などのセキュリティ警告ダイアログが表示されます。一度「完了」または「キャンセル」をクリックします。
  2. 画面左上のアップルメニューから「**システム設定**」を開き、「**プライバシーとセキュリティ**」を選択します。
  3. 「セキュリティ」の項目までスクロールすると、「"dicom-organizer" は使用がブロックされました」と表示されているので、「**このまま開く**」をクリックします。
  4. 利用者のログインパスワード（管理者権限は不要です）の入力を求められる場合がありますので入力し、確認ダイアログで「開く」を選択すると起動します（この操作は初回のみ必要です）。
- **Windows の場合**:
  1. アプリをダブルクリックした際、Windows Defender SmartScreen により「Windows によって PC が保護されました」と表示されます。
  2. 画面上の「**詳細情報**」リンクをクリックします。
  3. 右下に表示される「**実行**」ボタンをクリックすると起動します（初回のみ）。

#### インストール後の動作確認
- アプリを起動し、メニューバーの「ヘルプ」→「**動作確認（自己診断）を実行**」をクリックしてください。
- または、実行ファイルのパスを指定して自己診断フラグ `--self-test` とレポート保存オプション `--self-test-report` を付けて実行します:
  - macOS:
    ```bash
    /Applications/dicom-organizer.app/Contents/MacOS/dicom-organizer --self-test --self-test-report ~/Desktop/dicom-organizer-self-test.txt
    ```
  - Windows:
    - **PowerShell**（Windows 11 の既定ターミナル）:
      ```powershell
      .\dicom-organizer.exe --self-test --self-test-report $env:USERPROFILE\Desktop\dicom-organizer-self-test.txt
      ```
    - **コマンドプロンプト (cmd.exe)**:
      ```cmd
      dicom-organizer.exe --self-test --self-test-report %USERPROFILE%\Desktop\dicom-organizer-self-test.txt
      ```
    ※ Windows のアプリ版はコンソールに直接結果が出力されないことがあるため、生成されたレポートファイルを開いてすべての項目が `[PASS]` となっていることを確認してください。

#### オフライン環境への持ち込み
電子カルテ網や画像診断ワークステーション等のオフライン環境に持ち込む場合:
- ダウンロードした zip ファイルを記録媒体（USBメモリ等）経由でオフラインPCにコピーします。
- 任意のフォルダに展開するだけで即座に利用可能です。追加の通信やライブラリのダウンロードは一切発生しません。

#### 更新と旧版への復帰
- **更新**: 新しいリリースの zip をダウンロードして展開し、既存のアプリを置き換えます。過去の設定（前回選択したプロファイルや出力形式など）は保持されます。
- **旧版への復帰**: 最新版で予期せぬ動作があった場合、Releases ページから以前のバージョンの zip をダウンロードして置き換えることで、安全に旧版へ復帰できます。

#### アンインストール
1. アプリケーション本体を削除します:
   - macOS: `dicom-organizer.app` をゴミ箱に移動します。
   - Windows: 展開した `dicom-organizer` フォルダを削除します。
2. 設定ファイルを削除する場合（任意）:
   - macOS: `~/Library/Preferences/com.dicom-organizer.dicom-organizer.plist`
   - Windows（レジストリ）: `HKEY_CURRENT_USER\Software\dicom-organizer\dicom-organizer`
   - Linux: `~/.config/dicom-organizer/dicom-organizer.conf`

---

### 3. Python パッケージ版のセットアップ（CLI / Python GUI）

Python 3.11 以上の環境（自動テストで確認しているのは 3.11・3.12・3.13・3.14。GUI を使う場合は PySide6 の対応範囲に従い、2026-09 時点の PySide6 6.11.1 は 3.10 以上 3.15 未満）でコマンドラインツールやスクリプトとして利用する場合の手順です。

#### uv によるインストール
- CLI のみ:
  ```bash
  uv tool install dicom-organizer
  ```
- CLI + PySide6 GUI:
  ```bash
  uv tool install 'dicom-organizer[gui]'
  ```
- バージョンを指定してインストール（または旧版への復帰）:
  ```bash
  uv tool install 'dicom-organizer[gui]==0.2.0'
  ```

#### 更新とアンインストール
- 更新:
  ```bash
  uv tool upgrade dicom-organizer
  ```
- アンインストール:
  ```bash
  uv tool uninstall dicom-organizer
  ```

#### macOS 用軽量ランチャーについて
コマンド `dicom-organizer-gui-app` は、Python 版利用者が macOS の Dock や Spotlight から GUI を直接起動できるようにするための軽量ラッパーです。単体アプリ版（Standalone Desktop App）をお使いの方は、本コマンドではなく zip に同梱されている `dicom-organizer.app` を直接お使いください。

#### Python 版のオフライン導入
プラットフォーム固有のバイナリパッケージ（特に PySide6）は OS や CPU アーキテクチャごとに異なるため、対象のオフライン PC と**同じ OS・CPU アーキテクチャ**のオンライン PC で wheel を集める必要があります:
```bash
python3 -m pip download --dest ./wheelhouse "dicom-organizer[gui]"
```
`./wheelhouse` ディレクトリをオフライン環境へ持ち込み、`--no-index` オプションでインストールします:
```bash
uv tool install --no-index --find-links ./wheelhouse 'dicom-organizer[gui]'
```
