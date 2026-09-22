# Performance Benchmarks and Memory Usage / 性能ベンチマークとメモリ使用量

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

This document reports empirical performance benchmarks for `dicom-organizer`, including throughput (files/second), execution time, and peak memory consumption across different operational modes.
All numbers reported below are measured using `scripts/benchmark.py` and strictly sourced from empirical benchmark logs.

### 1. Measurement Conditions and Benchmark Environment

- **Measurement Script**: `scripts/benchmark.py` (included in the repository for reproducible verification).
  - Executed commands:
    - `python scripts/benchmark.py --files 1000 5000 20000 --matrix 256 --repeat 3`
    - `python scripts/benchmark.py --files 20000 --matrix 16 --repeat 3`
- **Benchmarked Code**: commit `415f165` (0.2.0 development branch).
- **Hardware & Environment**:
  - Processor: Apple M4 (logical cores 10).
  - System Memory: 24.0 GB RAM.
  - Operating System: macOS (Darwin 27.0.0, arm64).
  - Storage: Internal SSD (APFS). Source and destination directories resided on the same internal SSD.
  - Python Environment: Python 3.11.13, pydicom 3.0.2.
- **Dataset**: Synthetic MR images (100 images per series, 16 bit, uncompressed).
  - Matrix 256: average 128.9 KiB per file.
  - Matrix 16: average 1.4 KiB per file.
- **Protocol**: Each mode was executed 3 times in independent processes. Reported durations are the **median** values (with min–max ranges in parentheses). Maximum memory (RSS) represents the highest value observed across the 3 runs. Durations include Python process initialization and imports. All output counts matched input counts. Measurements occurred immediately after dataset creation with operating system file cache warm.

### 2. Benchmark Results: Realistic 128.9 KiB Files (Matrix 256)

| File Count | Series Count | Total Data | Mode | Seconds (Median) | Min–Max | Throughput (files/s) | MB/s | Peak Memory (RSS) |
|---:|---:|---:|---|---:|---|---:|---:|---:|
| 1,000 | 10 | 125.93 MB | Dry-run (`-n`) | 0.56 | 0.56〜0.56 | 1798.0 | — | 50.8 MB |
| 1,000 | 10 | 125.93 MB | List-only (`--list-only`) | 0.57 | 0.56〜0.57 | 1763.4 | — | 55.0 MB |
| 1,000 | 10 | 125.93 MB | Copy | 0.84 | 0.84〜0.85 | 1192.7 | 150.2 | 55.8 MB |
| 1,000 | 10 | 125.93 MB | Copy + Checksum | 0.97 | 0.97〜0.97 | 1035.5 | 130.4 | 56.1 MB |
| 5,000 | 50 | 629.64 MB | Dry-run (`-n`) | 2.57 | 2.57〜2.58 | 1943.1 | — | 107.7 MB |
| 5,000 | 50 | 629.64 MB | List-only (`--list-only`) | 2.56 | 2.54〜2.63 | 1949.7 | — | 126.8 MB |
| 5,000 | 50 | 629.64 MB | Copy | 3.90 | 3.88〜4.05 | 1280.7 | 161.3 | 128.5 MB |
| 5,000 | 50 | 629.64 MB | Copy + Checksum | 4.47 | 4.47〜4.50 | 1118.4 | 140.8 | 128.7 MB |
| 20,000 | 200 | 2518.61 MB | Dry-run (`-n`) | 10.31 | 10.24〜10.46 | 1939.0 | — | 322.4 MB |
| 20,000 | 200 | 2518.61 MB | List-only (`--list-only`) | 10.04 | 10.01〜10.05 | 1991.5 | — | 394.0 MB |
| 20,000 | 200 | 2518.61 MB | Copy | 21.20 | 17.48〜22.35 | 943.6 | 118.8 | 404.2 MB |
| 20,000 | 200 | 2518.61 MB | Copy + Checksum | 18.17 | 18.16〜18.25 | 1100.5 | 138.6 | 404.6 MB |

Note: The 20,000 copy run showed wider variance (17.48〜22.35 s), possibly due to writing approx. 2.5 GB to the internal SSD under varying disk states.

### 3. Benchmark Results: Lightweight 1.4 KiB Files (Matrix 16, Header Overhead)

| File Count | Series Count | Total Data | Mode | Seconds (Median) | Min–Max | Throughput (files/s) | Peak Memory (RSS) |
|---:|---:|---:|---|---:|---|---:|---:|
| 20,000 | 200 | 28.38 MB | Dry-run (`-n`) | 10.00 | 9.98〜10.03 | 2000.1 | 322.5 MB |
| 20,000 | 200 | 28.38 MB | List-only (`--list-only`) | 9.99 | 9.93〜10.02 | 2002.4 | 394.1 MB |
| 20,000 | 200 | 28.38 MB | Copy | 14.94 | 14.88〜15.15 | 1338.7 | 404.4 MB |
| 20,000 | 200 | 28.38 MB | Copy + Checksum | 15.64 | 15.54〜15.66 | 1278.7 | 404.5 MB |

### 4. Key Performance Insights

- **Header Parsing Throughput**: Dry-run and list-only achieve approximately 2,000 files per second (1939.0〜2002.4 files/s) on this machine regardless of file payload size, as header inspection dominates execution time.
- **Copy Throughput**: Copy reaches 943.6〜1338.7 files/s, while copy with checksum reaches 1035.5〜1278.7 files/s.
- **Memory Scaling**: Memory scales with file count because metadata rows are retained in memory before writing CSV outputs. Peak memory grew from 55.0 MB at 1,000 files to 394.0 MB at 20,000 files in list-only mode.
  - This corresponds to an empirical increase of approximately 18.3 KB per file: `(394.02 − 55.05) MB × 1024 ÷ 19,000`.
  - Theoretical estimate for 100,000 files in list-only mode (unmeasured extrapolation): `55.05 + 18.27 × 99,000 ÷ 1024 ≈ 1821.3 MB` (approx. 1.8 GB). When processing extremely large repositories (>100,000 files), executing across separate subdirectories is recommended to constrain memory usage.

### 5. Real Scanner Data Timings

From empirical verification on 2,157 candidate files (approx. 1.12 GB) on the same machine (measured in a single run; files may have resided in the operating system file cache from the preceding list-only execution):
- List-only (`--list-only`): 3.8 seconds (commit `415f165`; 3.9 seconds in `a656572`).
- Copy + Checksum: 4.5 seconds (commit `415f165`; 4.7 seconds in `a656572`).
- Peak RSS memory: approximately 110 MB (approx. 111 MB in `a656572`).

### 6. Unmeasured Conditions

- Performance on Windows and Intel Mac hardware, mechanical HDDs, USB external drives, network shares, and cold cache states has not been measured.
- Performance in the GUI application has not been benchmarked (though it shares the identical Python core engine).
- Actual time saved during clinical or research workflows will be measured during upcoming user research interviews.

---

<a id="japanese"></a>
## 日本語

本文書は、`dicom-organizer` の処理性能（毎秒処理ファイル数）、実行所要時間、および最大メモリ消費量（RSS）の実測値を報告するものです。
以下に記載するすべての数値は、リポジトリ同梱の `scripts/benchmark.py` を用いて計測された事実ファイル（`facts-performance.md`、`facts-realdata.md`）に厳密に基づいています。

### 1. 計測環境と計測条件

- **計測スクリプト**: `scripts/benchmark.py`（リポジトリ同梱。どなたでも同一手順で再検証可能です）。
  - 実行コマンド:
    - `python scripts/benchmark.py --files 1000 5000 20000 --matrix 256 --repeat 3`
    - `python scripts/benchmark.py --files 20000 --matrix 16 --repeat 3`
- **計測対象コード**: commit `415f165`（0.2.0 開発版）。
- **ハードウェアおよび環境**:
  - プロセッサ: Apple M4（論理 10 コア）。
  - メモリ: 24.0 GB RAM。
  - OS: macOS（Darwin 27.0.0、arm64）。
  - ストレージ: 内蔵 SSD（APFS）。同一 SSD 内で読み書きを実施。
  - 実行環境: Python 3.11.13、pydicom 3.0.2。
- **データセット**: 合成 MR 画像（1 シリーズ 100 画像、16 bit、非圧縮）。
  - 行列 256: 1 ファイル平均 128.9 KiB。
  - 行列 16: 1 ファイル平均 1.4 KiB。
- **計測方法**: 各モードを独立したプロセスで 3 回ずつ実行し、所要時間は **中央値**（括弧内は最小〜最大）。最大メモリ（RSS）は 3 回中の最大値。Python の起動時間を含みます。出力件数が入力件数と完全一致することを検証済み。OS のファイルキャッシュが温まった状態での計測値です。

### 2. 計測結果: 1 ファイル 128.9 KiB（行列 256）

| ファイル数 | シリーズ数 | データ総量 | 実行モード | 所要秒数（中央値） | 最小〜最大 | 処理速度 (files/s) | 転送速度 (MB/s) | 最大メモリ (RSS) |
|---:|---:|---:|---|---:|---|---:|---:|---:|
| 1,000 | 10 | 125.93 MB | 確認（dry-run） | 0.56 | 0.56〜0.56 | 1798.0 | — | 50.8 MB |
| 1,000 | 10 | 125.93 MB | 一覧のみ (`--list-only`) | 0.57 | 0.56〜0.57 | 1763.4 | — | 55.0 MB |
| 1,000 | 10 | 125.93 MB | コピー | 0.84 | 0.84〜0.85 | 1192.7 | 150.2 | 55.8 MB |
| 1,000 | 10 | 125.93 MB | コピー + チェックサム | 0.97 | 0.97〜0.97 | 1035.5 | 130.4 | 56.1 MB |
| 5,000 | 50 | 629.64 MB | 確認（dry-run） | 2.57 | 2.57〜2.58 | 1943.1 | — | 107.7 MB |
| 5,000 | 50 | 629.64 MB | 一覧のみ (`--list-only`) | 2.56 | 2.54〜2.63 | 1949.7 | — | 126.8 MB |
| 5,000 | 50 | 629.64 MB | コピー | 3.90 | 3.88〜4.05 | 1280.7 | 161.3 | 128.5 MB |
| 5,000 | 50 | 629.64 MB | コピー + チェックサム | 4.47 | 4.47〜4.50 | 1118.4 | 140.8 | 128.7 MB |
| 20,000 | 200 | 2518.61 MB | 確認（dry-run） | 10.31 | 10.24〜10.46 | 1939.0 | — | 322.4 MB |
| 20,000 | 200 | 2518.61 MB | 一覧のみ (`--list-only`) | 10.04 | 10.01〜10.05 | 1991.5 | — | 394.0 MB |
| 20,000 | 200 | 2518.61 MB | コピー | 21.20 | 17.48〜22.35 | 943.6 | 118.8 | 404.2 MB |
| 20,000 | 200 | 2518.61 MB | コピー + チェックサム | 18.17 | 18.16〜18.25 | 1100.5 | 138.6 | 404.6 MB |

※ 20,000 件のコピーにおけるばらつき（17.48〜22.35 秒）は、同一 SSD への約 2.5 GB の書き込みに伴う負荷などの可能性があります。

### 3. 計測結果: 1 ファイル 1.4 KiB（行列 16、ヘッダー処理の負荷確認）

| ファイル数 | シリーズ数 | データ総量 | 実行モード | 所要秒数（中央値） | 最小〜最大 | 処理速度 (files/s) | 最大メモリ (RSS) |
|---:|---:|---:|---|---:|---|---:|---:|
| 20,000 | 200 | 28.38 MB | 確認（dry-run） | 10.00 | 9.98〜10.03 | 2000.1 | 322.5 MB |
| 20,000 | 200 | 28.38 MB | 一覧のみ (`--list-only`) | 9.99 | 9.93〜10.02 | 2002.4 | 394.1 MB |
| 20,000 | 200 | 28.38 MB | コピー | 14.94 | 14.88〜15.15 | 1338.7 | 404.4 MB |
| 20,000 | 200 | 28.38 MB | コピー + チェックサム | 15.64 | 15.54〜15.66 | 1278.7 | 404.5 MB |

### 4. 計測結果から読み取れること

- **ヘッダー読み取り処理能力**: 確認および一覧のみモードでは、ファイルサイズ（1.4 KiB と 128.9 KiB）によらず毎秒約 2,000 ファイル（1939.0〜2002.4 files/s）を処理します。処理時間の大半は DICOM ヘッダーの解析が占めています。
- **ファイルコピー処理能力**: コピーは毎秒 943.6〜1338.7 ファイル、チェックサム付きコピーは毎秒 1035.5〜1278.7 ファイルを達成しています。
- **メモリ消費量の傾向**: 表出力前に全ファイルのメタデータをメモリに保持するため、メモリ消費はファイル数に比例して増加します。一覧のみモードでは 1,000 件で 55.0 MB、20,000 件で 394.0 MB となりました。
-   実測値に基づく 1 ファイルあたりの増加量は約 18.3 KB です: `(394.02 − 55.05) MB × 1024 ÷ 19,000`。
-   10 万件での理論推定値（未計測の推定計算）: `55.05 + 18.27 × 99,000 ÷ 1024 ≈ 1821.3 MB`（約 1.8 GB）。10 万件を超える大規模データでは、フォルダを分割して実行することを推奨します。

### 5. 実機データ（MR）での所要時間

同一マシンにおいて、実機 MR データ 2,157 候補ファイル（約 1.12 GB）を処理した際の実測値（1 回のみの計測であり、直前の一覧作成によりファイルが OS のファイルキャッシュに載っていた可能性があります）:
- 一覧のみ (`--list-only`): 3.8 秒（commit `415f165`。`a656572` では 3.9 秒）。
- 通常の整理（コピー + チェックサム）: 4.5 秒（commit `415f165`。`a656572` では 4.7 秒）。
- プロセス全体の最大メモリ (RSS): 約 110 MB（`a656572` では約 111 MB）。

### 6. 未計測の事項

- Windows、Intel Mac、HDD、外付け USB ドライブ、ネットワーク共有フォルダでの性能、および OS キャッシュが空の状態での性能は未計測です。
- GUI 操作時のオーバーヘッドは未計測です（CLI と同一の中核エンジンを使用します）。
- 手作業と比較した実務作業時間の短縮効果は、今後の利用者調査にて計測を予定しています。
