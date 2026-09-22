# Third-Party Software Notices and Information / 第三者ソフトウェアライセンス告知

This list is a distribution guide and is not legal advice.
この一覧は配布の手引きであり、法的助言ではない。配布前に各ライセンス本文を確認すること。

This standalone distribution of `dicom-organizer` packages and redistributes third-party software components under their respective licenses.
単体アプリ版 `dicom-organizer` には、以下の第三者ソフトウェアコンポーネントが同梱され、それぞれのライセンスの下で再配布されています。

---

## 1. Python

- **Project**: Python
- **License**: Python Software Foundation (PSF) License
- **Upstream / Source**: <https://www.python.org/>
- **Description**: Python is an interpreted, high-level, general-purpose programming language. The embedded Python runtime is distributed under the terms of the PSF License Agreement.

---

## 2. pydicom

- **Project**: pydicom
- **License**: MIT License
- **Upstream / Source**: <https://github.com/pydicom/pydicom>
- **Description**: A pure Python package for working with DICOM files. Distributed under the permissive MIT license.

---

## 3. PySide6 / Qt for Python and Qt

- **Project**: PySide6 (Qt for Python) & Qt
- **License**: GNU Lesser General Public License version 3 (LGPLv3)
- **Upstream / Source**:
  - Qt Source Code: <https://download.qt.io/>
  - Qt for Python Source Code: <https://code.qt.io/>
- **LGPLv3 Compliance Notice**:
  - `dicom-organizer` links dynamically against Qt and PySide6 libraries provided as separate shared libraries / dynamic link libraries (`.dylib`, `.so`, or `.dll`).
  - In accordance with the LGPLv3, users are permitted to modify or replace the Qt / PySide6 shared library binaries with compatible versions for their own use.
  - LGPLv3 遵守に関する告知: 本配布物では Qt および PySide6 を動的リンク（共有ライブラリ形式）で使用しています。利用者は LGPLv3 の規定に基づき、同梱されている Qt / PySide6 の動的ライブラリを互換性のある別バージョンに差し替えて実行・利用することが可能です。

---

## 4. PyInstaller Bootloader

- **Project**: PyInstaller Bootloader
- **License**: GNU General Public License version 2 (GPLv2) with Bootloader Exception
- **Upstream / Source**: <https://github.com/pyinstaller/pyinstaller>
- **Description**: The PyInstaller bootloader is distributed under the GNU General Public License version 2 or later with a special exception permitting distribution of packaged applications without subjecting the bundled application code to the terms of the GPL.
