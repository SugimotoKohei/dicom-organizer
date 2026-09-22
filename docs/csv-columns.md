# CSV Column Dictionary

This document provides a comprehensive dictionary of all CSV columns output by `dicom-organizer`, including their definitions, measurement units, data sources, missing (`N/A`) conditions, and applicable metadata profiles.

For the schema architecture, file row scopes, and folder layout options, see [CSV Schema (csv-schema.md)](csv-schema.md).

## Conventions

- **Missing Values**: Represented as `N/A`.
- **Multiple Values**: Distinct values within a series or across frames are joined with `|`.
- **DICOM Multi-Valued Attributes**: Standard backslash `\` delimiter is preserved for multi-valued DICOM elements (VM > 1).
- **Dates and Times**: Dates follow DICOM DA format (`YYYYMMDD`); times follow DICOM TM format as-is.
- **Character Encoding**: CSV files are encoded in UTF-8 with BOM (`utf-8-sig`) for Excel compatibility.
- **Custom Tags**: Requested via `--dicom-tag` as `DICOM_<Keyword>` (or user-specified alias) with user-selected DICOM tag sources.

## Column Specifications (English)

| Column | Description | Unit | Source | Missing (N/A) Condition | Profiles |
|---|---|---|---|---|---|
| `OrganizedFileName` | POSIX relative path of the organized file within the output directory |  | organizer: destination path relative to output root | in list-only mode (--list-only) or if file was not placed/organized | all |
| `StudyFolder` | POSIX relative path of the study directory from output root |  | organizer: study folder path derived from layout and metadata | never missing; always determined from organization layout and metadata | all |
| `SeriesFolder` | POSIX relative path of the series directory from output root |  | organizer: series folder path derived from series template | never missing; always determined from series folder label template | all |
| `SeriesUID` | Unique identifier for the Series |  | SeriesInstanceUID (0020,000E) | attribute absent in the DICOM header | all |
| `SOPInstanceUID` | Unique identifier for the SOP Instance (image object) |  | SOPInstanceUID (0008,0018) | attribute absent in the DICOM header | all |
| `SeriesNumber` | Integer number identifying the series within the study (6-digit zero-padded) |  | SeriesNumber (0020,0011) | never missing; formatted as a 6-digit zero-padded integer (e.g. '000001'), or sanitized string if non-numeric; defaults to '000000' when attribute is absent | all |
| `SeriesDescription` | User-provided or operator description of the series |  | SeriesDescription (0008,103E) | attribute absent in the DICOM header | all |
| `ProtocolName` | User-defined description of the acquisition protocol |  | ProtocolName (0018,1030) | attribute absent in the DICOM header | all |
| `FileCount` | Number of DICOM files belonging to the series |  | derived: count of DICOM files in series | never missing in series summary; N/A prior to series aggregation | all |
| `InstanceNumber` | Number identifying the instance (slice/image) within the series |  | InstanceNumber (0020,0013) | attribute absent in the DICOM header | all |
| `AcquisitionDate` | Date the acquisition of data started (YYYYMMDD) |  | AcquisitionDate (0008,0022); fallback: StudyDate (0008,0020) | both AcquisitionDate and StudyDate absent in the DICOM header | all |
| `AcquisitionTime` | Time the acquisition of data started (DICOM TM format) |  | AcquisitionTime (0008,0032) | attribute absent in the DICOM header | all |
| `StudyDate` | Date the study started (YYYYMMDD) |  | StudyDate (0008,0020) | attribute absent in the DICOM header | all |
| `StudyTime` | Time the study started (DICOM TM format) |  | StudyTime (0008,0030) | attribute absent in the DICOM header | all |
| `SeriesDate` | Date the series started (YYYYMMDD) |  | SeriesDate (0008,0021) | attribute absent in the DICOM header | all |
| `SeriesTime` | Time the series started (DICOM TM format) |  | SeriesTime (0008,0031) | attribute absent in the DICOM header | all |
| `PatientName` | Patient's full name (pseudonymized under hash, N/A under drop) |  | PatientName (0010,0010) | attribute absent in the DICOM header, or --patient-mode drop | all |
| `PatientID` | Primary hospital identifier for the patient (pseudonymized under hash, N/A under drop) |  | PatientID (0010,0020) | attribute absent in the DICOM header, or --patient-mode drop | all |
| `PatientIDHash` | First 16 hexadecimal characters of SHA-256 digest of PatientID |  | derived: SHA-256 digest of PatientID | PatientID absent in the DICOM header, or --patient-mode drop | all |
| `PatientNameHash` | First 16 hexadecimal characters of SHA-256 digest of PatientName |  | derived: SHA-256 digest of PatientName | PatientName absent in the DICOM header, or --patient-mode drop | all |
| `Modality` | Type of equipment that originally acquired data (e.g. MR, CT, US, XA, PT) |  | Modality (0008,0060) | attribute absent in the DICOM header | all |
| `SOPClassUID` | Unique identifier for the SOP Class |  | SOPClassUID (0008,0016) | attribute absent in the DICOM header | all |
| `FOV_HxW_mm` | Field of view height and width in mm (PixelSpacing * Rows x Columns) | mm | derived: PixelSpacing * (Rows x Columns) | PixelSpacing, Rows, or Columns absent or non-numeric | all |
| `Matrix_RowsxCols` | Image matrix dimensions in pixels (RowsxColumns) |  | derived: Rows x Columns | Rows or Columns absent in the DICOM header | all |
| `SliceThickness_mm` | Nominal slice thickness in mm | mm | SliceThickness (0018,0050); Enhanced: PixelMeasuresSequence.SliceThickness | attribute absent in the header or functional groups | all |
| `SpacingBetweenSlices_mm` | Distance between adjacent slice centers in mm along normal vector | mm | SpacingBetweenSlices (0018,0088); Enhanced: PixelMeasuresSequence.SpacingBetweenSlices | attribute absent in the header or functional groups | all |
| `SliceLocation_mm` | Relative position of slice in mm | mm | SliceLocation (0020,1041) | attribute absent in the DICOM header | all |
| `Manufacturer` | Manufacturer of the equipment that produced the DICOM data |  | Manufacturer (0008,0070) | attribute absent in the DICOM header | all |
| `ManufacturerModelName` | Manufacturer's model name of the equipment |  | ManufacturerModelName (0008,1090) | attribute absent in the DICOM header | all |
| `SourceFileName` | POSIX relative path of the source file from input root directory |  | organizer: relative path of source file from input root | never missing for scanned candidate files | all |
| `ImageType` | Image identification characteristics separated by backslashes |  | ImageType (0008,0008) | attribute absent in the DICOM header | all |
| `Rows` | Number of rows in the image raster |  | Rows (0028,0010) | attribute absent in the DICOM header | all |
| `Columns` | Number of columns in the image raster |  | Columns (0028,0011) | attribute absent in the DICOM header | all |
| `PixelSpacing` | Physical spacing between pixel centers (row\column spacing in mm) | mm | PixelSpacing (0028,0030); Enhanced: PixelMeasuresSequence.PixelSpacing | attribute absent in the header or functional groups | all |
| `ImagePositionPatient` | x, y, and z coordinates of the upper left corner of the image in patient coordinates (mm) | mm | ImagePositionPatient (0020,0032); Enhanced: PlanePositionSequence.ImagePositionPatient | attribute absent in the header or functional groups | all |
| `ImageOrientationPatient` | Direction cosines of the first row and first column with respect to the patient |  | ImageOrientationPatient (0020,0037); Enhanced: PlaneOrientationSequence.ImageOrientationPatient | attribute absent in the header or functional groups | all |
| `PatientPosition` | Patient position descriptor relative to equipment (e.g. HFS, FFS) |  | PatientPosition (0018,5100) | attribute absent in the DICOM header | all |
| `FrameOfReferenceUID` | Unique identifier of the spatial Frame of Reference |  | FrameOfReferenceUID (0020,0052) | attribute absent in the DICOM header | all |
| `StudyInstanceUID` | Unique identifier for the Study |  | StudyInstanceUID (0020,000D) | attribute absent in the DICOM header | all |
| `IsNormalized` | Flag indicating whether image is intensity-normalized (true/false derived from ImageType) |  | derived: whether ImageType contains NORM | never missing; reports 'true' if ImageType contains 'NORM', otherwise 'false' (including when ImageType attribute is absent) | all |
| `ScanDuration` | Total scan duration formatted as HH:MM:SS | HH:MM:SS | derived: AcquisitionDuration (0018,9073) in seconds; GE private GEMS_ACQU_01 (0019,105A) in microseconds / 1e6; or Siemens ASCCONV lTotalScanTimeSec in seconds; formatted as HH:MM:SS | scan duration tag not found or non-positive | all |
| `ScanDurationSource` | Identifier of the tag or element where scan duration was extracted |  | derived: tag or element where scan duration was found | scan duration tag not found | all |
| `NumberOfFrames` | Number of frames in a multi-frame DICOM object |  | NumberOfFrames (0028,0008) | attribute absent in the DICOM header (single-frame object) | all |
| `FrameVaryingAttributes` | Attribute columns that vary across frames in PerFrameFunctionalGroupsSequence joined with \| ('none' if identical; appends PhaseEncodingDirectionPatient at the end if orientation varies) |  | derived: columns whose values vary across frames in PerFrameFunctionalGroupsSequence | object has no PerFrameFunctionalGroupsSequence | all |
| `TR_ms` | Repetition time in ms | ms | RepetitionTime (0018,0080); Enhanced: MRTimingAndRelatedParametersSequence.RepetitionTime | attribute absent in the header, or not an MR object | mr |
| `TE_ms` | Echo time in ms | ms | EchoTime (0018,0081); Enhanced: MREchoSequence.EffectiveEchoTime | attribute absent in the header, or not an MR object | mr |
| `EchoCount` | Number of unique echo times in the series |  | derived: number of unique TE_ms values in the series | not an MR series, or no valid echo times found in series | mr |
| `EchoTimes_ms` | List of unique echo times in the series joined by \| in ms | ms | derived: unique TE_ms values in the series joined by \| | not an MR series, or no valid echo times found in series | mr |
| `PixelBandwidth_Hz_per_px` | Equivalent pixel bandwidth in Hz/pixel | Hz/pixel | PixelBandwidth (0018,0095); Enhanced: MRImagingModifierSequence.PixelBandwidth | attribute absent in the header, or not an MR object | mr |
| `EchoTrainLength` | Number of lines in k-space acquired per excitation (ETL) |  | EchoTrainLength (0018,0091); Enhanced: MRTimingAndRelatedParametersSequence.EchoTrainLength | attribute absent in the header, or not an MR object | mr |
| `FlipAngle_deg` | Steady-state flip angle in degrees | deg | FlipAngle (0018,1314); Enhanced: MRTimingAndRelatedParametersSequence.FlipAngle | attribute absent in the header, or not an MR object | mr |
| `NumberOfAverages` | Number of times each line of k-space was acquired (NEX/averages) |  | NumberOfAverages (0018,0083); Enhanced: MRAveragesSequence.NumberOfAverages | attribute absent in the header, or not an MR object | mr |
| `MagneticFieldStrength_T` | Nominal field strength of the MR magnet in Tesla | T | MagneticFieldStrength (0018,0087) | attribute absent in the header, or not an MR object | mr |
| `ScanningSequence` | Description of the type of data taken (e.g. SE, GE, IR, EP) |  | ScanningSequence (0018,0020) | attribute absent in the header, or not an MR object | mr |
| `SequenceVariant` | Variant of the scanning sequence (e.g. SK, SP, SS, MTC) |  | SequenceVariant (0018,0021) | attribute absent in the header, or not an MR object | mr |
| `SequenceName` | User or manufacturer sequence name |  | SequenceName (0018,0024); Philips fallback: private sequence (2005,140F)[0].PulseSequenceName | attribute absent in the header, or not an MR object | mr |
| `InversionTime_ms` | Inversion time in ms after 180-degree prep pulse | ms | InversionTime (0018,0082); Enhanced: MRModifierSequence.InversionTimes | attribute absent in the header, or not an MR object | mr |
| `EchoNumbers` | Echo number within the sequence |  | EchoNumbers (0018,0086) | attribute absent in the header, or not an MR object | mr |
| `AcquisitionMatrix` | Dimensions of the acquired frequency and phase encoding steps |  | AcquisitionMatrix (0018,1310) | attribute absent in the header, or not an MR object | mr |
| `NumberOfPhaseEncodingSteps` | Total number of phase encoding steps |  | NumberOfPhaseEncodingSteps (0018,0089) | attribute absent in the header, or not an MR object | mr |
| `PercentSampling` | Fraction of acquisition matrix lines sampled (percent) | % | PercentSampling (0018,0093) | attribute absent in the header, or not an MR object | mr |
| `PercentPhaseFOV` | Ratio of phase field of view to frequency field of view (percent) | % | PercentPhaseFieldOfView (0018,0094) | attribute absent in the header, or not an MR object | mr |
| `ParallelReductionFactorInPlane` | Parallel imaging acceleration factor in-plane |  | ParallelReductionFactorInPlane (0018,9069); Enhanced: MRModifierSequence.ParallelReductionFactorInPlane; Siemens fallback: sPat.lAccelFactPE | attribute absent in the header, or not an MR object | mr |
| `SAR` | Calculated whole body Specific Absorption Rate in W/kg | W/kg | SAR (0018,1316) | attribute absent in the header, or not an MR object | mr |
| `InPlanePhaseEncodingDirection` | Axes of phase encoding relative to image row and column (ROW, COL, or COLUMN) |  | InPlanePhaseEncodingDirection (0018,1312); Enhanced: MRFOVGeometrySequence.InPlanePhaseEncodingDirection | attribute absent in the header, or not an MR object | mr |
| `PhaseEncodingDirectionPatient` | Patient-relative cardinal direction arrow of phase encoding (e.g. A→P, P→A, R→L, L→R, F→H, H→F; joined with \| across frames if varying) |  | derived: patient-relative cardinal axis calculated from InPlanePhaseEncodingDirection and ImageOrientationPatient | attribute absent in the header, orientation invalid, or not an MR object | mr |
| `ReceiveCoilName` | Name of the receive coil used |  | ReceiveCoilName (0018,1250) | attribute absent in the header, or not an MR object | mr |
| `MRAcquisitionType` | Identification of data acquisition technique (2D or 3D) |  | MRAcquisitionType (0018,0023) | attribute absent in the header, or not an MR object | mr |
| `SiemensChannelMixing` | Siemens private channel mixing descriptor |  | Siemens private tag (0021,1176) | attribute absent in the header, or Manufacturer does not contain 'siemens' | mr |
| `SiemensCoilElement` | Siemens private coil element identifier for the instance |  | Siemens private tag (0021,114F) | attribute absent in the header, or Manufacturer does not contain 'siemens' | mr |
| `CoilElementCount` | Number of distinct coil elements used in the series |  | derived: number of unique SiemensCoilElement values in the series | not a Siemens MR series, or no coil elements found in series | mr |
| `CoilElements` | List of distinct coil elements in the series joined by \| |  | derived: unique SiemensCoilElement values in the series joined by \| | not a Siemens MR series, or no coil elements found in series | mr |
| `SiemensIceDims` | Siemens private ICE dimension string (e.g. CH_ECHO) |  | Siemens private tag (0021,118E) | attribute absent in the header, or Manufacturer does not contain 'siemens' | mr |
| `SiemensIceDimChannel` | Siemens ICE channel dimension index parsed from SiemensIceDims |  | derived: first component of SiemensIceDims (0021,118E) | SiemensIceDims absent, or Manufacturer does not contain 'siemens' | mr |
| `SiemensIceDimEcho` | Siemens ICE echo dimension index parsed from SiemensIceDims |  | derived: second component of SiemensIceDims (0021,118E) | SiemensIceDims absent or lacks echo index, or Manufacturer does not contain 'siemens' | mr |
| `KVP_kV` | Peak kilo voltage output of the X-ray generator in kV | kV | KVP (0018,0060) | attribute absent in the header, or not a CT/XA object | ct, xa |
| `XRayTubeCurrent_mA` | X-ray tube current in mA | mA | XRayTubeCurrent (0018,1151) | attribute absent in the header, or not a CT/XA object | ct, xa |
| `ExposureTime_ms` | Exposure time in ms | ms | ExposureTime (0018,1150) | attribute absent in the header, or not a CT/XA object | ct, xa |
| `ConvolutionKernel` | Label describing the convolution kernel or reconstruction algorithm |  | ConvolutionKernel (0018,1210) | attribute absent in the header, or not a CT object | ct |
| `ReconstructionDiameter_mm` | Diameter in mm of the region from which the image was reconstructed | mm | ReconstructionDiameter (0018,1100) | attribute absent in the header, or not a CT object | ct |
| `TransducerData` | Transducer information descriptor |  | TransducerData (0018,5010) | attribute absent in the header, or not an US object | us |
| `TransducerType` | Type of transducer used for ultrasound scan (e.g. SECTOR, LINEAR) |  | TransducerType (0018,6031) | attribute absent in the header, or not an US object | us |
| `MechanicalIndex` | Mechanical Index (MI) acoustic output metric |  | MechanicalIndex (0018,5022) | attribute absent in the header, or not an US object | us |
| `SoftTissueThermalIndex` | Soft Tissue Thermal Index (TIS) acoustic output metric |  | SoftTissueThermalIndex (0018,5027) | attribute absent in the header, or not an US object | us |
| `BoneThermalIndex` | Bone Thermal Index (TIB) acoustic output metric |  | BoneThermalIndex (0018,5024) | attribute absent in the header, or not an US object | us |
| `CranialThermalIndex` | Cranial Bone Thermal Index (TIC) acoustic output metric |  | CranialThermalIndex (0018,5026) | attribute absent in the header, or not an US object | us |
| `UltrasoundColorDataPresent` | Flag indicating whether color data is present in ultrasound image |  | UltrasoundColorDataPresent (0028,0014) | attribute absent in the header, or not an US object | us |
| `FrameTime_ms` | Nominal time per frame in ms for XA multi-frame image | ms | FrameTime (0018,1063) | attribute absent in the header, or not an XA object | xa |
| `DistanceSourceToDetector_mm` | Distance in mm from source to detector | mm | DistanceSourceToDetector (0018,1110) | attribute absent in the header, or not an XA object | xa |
| `DistanceSourceToPatient_mm` | Distance in mm from source to isocenter/patient | mm | DistanceSourceToPatient (0018,1111) | attribute absent in the header, or not an XA object | xa |
| `Radiopharmaceutical` | Name of the radiopharmaceutical agent administered |  | RadiopharmaceuticalInformationSequence[0].Radiopharmaceutical (0018,0031) | sequence absent in the header, or not a PT object | pt |
| `RadionuclideTotalDose_Bq` | Total radionuclide dose administered in Becquerels (Bq) | Bq | RadiopharmaceuticalInformationSequence[0].RadionuclideTotalDose (0018,1074) | sequence absent in the header, or not a PT object | pt |
| `RadionuclideHalfLife_s` | Radionuclide physical half-life in seconds | s | RadiopharmaceuticalInformationSequence[0].RadionuclideHalfLife (0018,1075) | sequence absent in the header, or not a PT object | pt |
| `DecayCorrection` | Real-world value decay correction type (NONE, START, ADMIN) |  | DecayCorrection (0054,1102) | attribute absent in the header, or not a PT object | pt |
| `Status` | Processing outcome status for candidate file (organized, listed, planned, skipped, not_processed) |  | organizer: processing outcome status | never missing (always populated with processing status) | all |
| `Reason` | Reason code explaining skipped, unplaced, or duplicate conflict status |  | organizer: skip, unplaced, or duplicate reason code | file is normally organized or listed without conflicts | all |
| `Detail` | Short English detail or conflict explanation |  | organizer: additional explanation or conflict detail | no additional detail is applicable | all |
| `DuplicateOf` | POSIX relative path of first-encountered matching file sharing the same SOPInstanceUID or identical content |  | organizer: relative path of first-encountered file with same SOPInstanceUID or identical content | file is not a duplicate of another file | all |
| `SizeBytes` | File size in bytes | bytes | organizer: file size in bytes from filesystem | file could not be read or does not exist | all |
| `SHA256` | SHA-256 hex digest of the file contents |  | organizer: SHA-256 hex digest of file contents | checksum not requested via --checksum and file not involved in duplicate comparison | all |

---

## 日本語 (Japanese)

この文書は `dicom-organizer` が出力するすべての CSV 列の意味、単位、取得元、N/A（欠損）になる条件、および対象プロファイルの完全な一覧です。

出力ファイル全体の構成やフォルダレイアウトについては [CSV スキーマ (csv-schema.md)](csv-schema.md) を参照してください。

### 値の規則

- **欠損値**: `N/A` で表記されます。
- **シリーズ・フレーム間の複数値**: シリーズ内またはフレーム間で値が複数存在する場合、重複を除いて `|` で連結されます。
- **DICOM 多値属性**: DICOM の多値要素（VM > 1）は標準のバックスラッシュ `\` で区切られます。
- **日付・時刻**: 日付は DICOM DA 形式（`YYYYMMDD`）、時刻は DICOM TM 形式をそのまま出力します。
- **文字コード**: Excel でそのまま開けるよう、UTF-8 BOM 付き（`utf-8-sig`）で出力されます。
- **追加タグ**: `--dicom-tag` で指定したタグは `DICOM_<Keyword>`（または指定名）として出力されます。

### 列定義一覧

| 列名 | 意味 | 単位 | 取得元 | N/A になる条件 | 対象プロファイル |
|---|---|---|---|---|---|
| `OrganizedFileName` | 出力ディレクトリ配下における整理後ファイルのPOSIX相対パス |  | organizer: destination path relative to output root | in list-only mode (--list-only) or if file was not placed/organized | 共通 |
| `StudyFolder` | 出力ルートからの検査フォルダのPOSIX相対パス |  | organizer: study folder path derived from layout and metadata | never missing; always determined from organization layout and metadata | 共通 |
| `SeriesFolder` | 出力ルートからのシリーズフォルダのPOSIX相対パス |  | organizer: series folder path derived from series template | never missing; always determined from series folder label template | 共通 |
| `SeriesUID` | シリーズを一意に識別するUID |  | SeriesInstanceUID (0020,000E) | attribute absent in the DICOM header | 共通 |
| `SOPInstanceUID` | SOPインスタンス（画像オブジェクト）を一意に識別するUID |  | SOPInstanceUID (0008,0018) | attribute absent in the DICOM header | 共通 |
| `SeriesNumber` | 検査内でのシリーズ番号（6桁ゼロ埋め整数表記） |  | SeriesNumber (0020,0011) | never missing; formatted as a 6-digit zero-padded integer (e.g. '000001'), or sanitized string if non-numeric; defaults to '000000' when attribute is absent | 共通 |
| `SeriesDescription` | シリーズの記述・説明 |  | SeriesDescription (0008,103E) | attribute absent in the DICOM header | 共通 |
| `ProtocolName` | 撮像プロトコル名 |  | ProtocolName (0018,1030) | attribute absent in the DICOM header | 共通 |
| `FileCount` | シリーズ内のDICOMファイル総数 |  | derived: count of DICOM files in series | never missing in series summary; N/A prior to series aggregation | 共通 |
| `InstanceNumber` | シリーズ内のインスタンス番号（スライス番号） |  | InstanceNumber (0020,0013) | attribute absent in the DICOM header | 共通 |
| `AcquisitionDate` | データ収集開始日（YYYYMMDD形式） |  | AcquisitionDate (0008,0022); fallback: StudyDate (0008,0020) | both AcquisitionDate and StudyDate absent in the DICOM header | 共通 |
| `AcquisitionTime` | データ収集開始時刻（DICOM TM形式） |  | AcquisitionTime (0008,0032) | attribute absent in the DICOM header | 共通 |
| `StudyDate` | 検査開始日（YYYYMMDD形式） |  | StudyDate (0008,0020) | attribute absent in the DICOM header | 共通 |
| `StudyTime` | 検査開始時刻（DICOM TM形式） |  | StudyTime (0008,0030) | attribute absent in the DICOM header | 共通 |
| `SeriesDate` | シリーズ開始日（YYYYMMDD形式） |  | SeriesDate (0008,0021) | attribute absent in the DICOM header | 共通 |
| `SeriesTime` | シリーズ開始時刻（DICOM TM形式） |  | SeriesTime (0008,0031) | attribute absent in the DICOM header | 共通 |
| `PatientName` | 患者氏名（hash時は仮名化、drop時はN/A） |  | PatientName (0010,0010) | attribute absent in the DICOM header, or --patient-mode drop | 共通 |
| `PatientID` | 患者ID（hash時は仮名化、drop時はN/A） |  | PatientID (0010,0020) | attribute absent in the DICOM header, or --patient-mode drop | 共通 |
| `PatientIDHash` | 患者IDのSHA-256ダイジェスト先頭16文字（drop時はN/A） |  | derived: SHA-256 digest of PatientID | PatientID absent in the DICOM header, or --patient-mode drop | 共通 |
| `PatientNameHash` | 患者氏名のSHA-256ダイジェスト先頭16文字（drop時はN/A） |  | derived: SHA-256 digest of PatientName | PatientName absent in the DICOM header, or --patient-mode drop | 共通 |
| `Modality` | 撮像モダリティ種別（MR, CT, US, XA, PTなど） |  | Modality (0008,0060) | attribute absent in the DICOM header | 共通 |
| `SOPClassUID` | SOPクラスを一意に識別するUID |  | SOPClassUID (0008,0016) | attribute absent in the DICOM header | 共通 |
| `FOV_HxW_mm` | 撮像視野サイズ（高さx幅、mm単位） | mm | derived: PixelSpacing * (Rows x Columns) | PixelSpacing, Rows, or Columns absent or non-numeric | 共通 |
| `Matrix_RowsxCols` | 画像マトリクス行列サイズ（行数x列数） |  | derived: Rows x Columns | Rows or Columns absent in the DICOM header | 共通 |
| `SliceThickness_mm` | 公称スライス厚（mm単位） | mm | SliceThickness (0018,0050); Enhanced: PixelMeasuresSequence.SliceThickness | attribute absent in the header or functional groups | 共通 |
| `SpacingBetweenSlices_mm` | 隣接スライス中心間の距離（スライス間隔、mm単位） | mm | SpacingBetweenSlices (0018,0088); Enhanced: PixelMeasuresSequence.SpacingBetweenSlices | attribute absent in the header or functional groups | 共通 |
| `SliceLocation_mm` | スライス位置の相対座標（mm単位） | mm | SliceLocation (0020,1041) | attribute absent in the DICOM header | 共通 |
| `Manufacturer` | 装置製造メーカー名 |  | Manufacturer (0008,0070) | attribute absent in the DICOM header | 共通 |
| `ManufacturerModelName` | 装置モデル名 |  | ManufacturerModelName (0008,1090) | attribute absent in the DICOM header | 共通 |
| `SourceFileName` | 入力ルートディレクトリからの元ファイルのPOSIX相対パス |  | organizer: relative path of source file from input root | never missing for scanned candidate files | 共通 |
| `ImageType` | 画像識別特性（バックスラッシュ区切りの多値文字列） |  | ImageType (0008,0008) | attribute absent in the DICOM header | 共通 |
| `Rows` | 画像の行数（ピクセル数） |  | Rows (0028,0010) | attribute absent in the DICOM header | 共通 |
| `Columns` | 画像の列数（ピクセル数） |  | Columns (0028,0011) | attribute absent in the DICOM header | 共通 |
| `PixelSpacing` | ピクセル中心間距離（行間隔\列間隔、mm単位） | mm | PixelSpacing (0028,0030); Enhanced: PixelMeasuresSequence.PixelSpacing | attribute absent in the header or functional groups | 共通 |
| `ImagePositionPatient` | 患者座標系における画像左上ピクセルのx, y, z座標（mm単位） | mm | ImagePositionPatient (0020,0032); Enhanced: PlanePositionSequence.ImagePositionPatient | attribute absent in the header or functional groups | 共通 |
| `ImageOrientationPatient` | 患者座標系に対する画像の第1行および第1列の方向余弦 |  | ImageOrientationPatient (0020,0037); Enhanced: PlaneOrientationSequence.ImageOrientationPatient | attribute absent in the header or functional groups | 共通 |
| `PatientPosition` | 装置に対する患者の体位記述子（HFS, FFSなど） |  | PatientPosition (0018,5100) | attribute absent in the DICOM header | 共通 |
| `FrameOfReferenceUID` | 空間座標基準系（Frame of Reference）を一意に識別するUID |  | FrameOfReferenceUID (0020,0052) | attribute absent in the DICOM header | 共通 |
| `StudyInstanceUID` | 検査を一意に識別するUID |  | StudyInstanceUID (0020,000D) | attribute absent in the DICOM header | 共通 |
| `IsNormalized` | 画像が強度補正（NORM）済みかどうかを示すフラグ（true/false） |  | derived: whether ImageType contains NORM | never missing; reports 'true' if ImageType contains 'NORM', otherwise 'false' (including when ImageType attribute is absent) | 共通 |
| `ScanDuration` | 総撮像時間（スキャン所要時間、HH:MM:SS形式） | HH:MM:SS | derived: AcquisitionDuration (0018,9073) in seconds; GE private GEMS_ACQU_01 (0019,105A) in microseconds / 1e6; or Siemens ASCCONV lTotalScanTimeSec in seconds; formatted as HH:MM:SS | scan duration tag not found or non-positive | 共通 |
| `ScanDurationSource` | 撮像時間の取得元となったタグまたは要素識別子 |  | derived: tag or element where scan duration was found | scan duration tag not found | 共通 |
| `NumberOfFrames` | マルチフレームDICOMオブジェクトのフレーム数 |  | NumberOfFrames (0028,0008) | attribute absent in the DICOM header (single-frame object) | 共通 |
| `FrameVaryingAttributes` | マルチフレーム画像内でフレームごとに値が変動する列名一覧（\|区切り、変動なし時はnone。向きが変動する場合は末尾にPhaseEncodingDirectionPatientが追加される） |  | derived: columns whose values vary across frames in PerFrameFunctionalGroupsSequence | object has no PerFrameFunctionalGroupsSequence | 共通 |
| `TR_ms` | 繰り返し時間（TR、ms単位） | ms | RepetitionTime (0018,0080); Enhanced: MRTimingAndRelatedParametersSequence.RepetitionTime | attribute absent in the header, or not an MR object | mr |
| `TE_ms` | エコー時間（TE、ms単位） | ms | EchoTime (0018,0081); Enhanced: MREchoSequence.EffectiveEchoTime | attribute absent in the header, or not an MR object | mr |
| `EchoCount` | シリーズ内のエコー数（固有TE値の件数） |  | derived: number of unique TE_ms values in the series | not an MR series, or no valid echo times found in series | mr |
| `EchoTimes_ms` | シリーズ内の固有エコー時間一覧（\|区切り、ms単位） | ms | derived: unique TE_ms values in the series joined by \| | not an MR series, or no valid echo times found in series | mr |
| `PixelBandwidth_Hz_per_px` | ピクセルあたりの等価受信帯域幅（Hz/pixel単位） | Hz/pixel | PixelBandwidth (0018,0095); Enhanced: MRImagingModifierSequence.PixelBandwidth | attribute absent in the header, or not an MR object | mr |
| `EchoTrainLength` | エコートレイン長（ETL、1励起あたりのk空間充填ライン数） |  | EchoTrainLength (0018,0091); Enhanced: MRTimingAndRelatedParametersSequence.EchoTrainLength | attribute absent in the header, or not an MR object | mr |
| `FlipAngle_deg` | フリップ角（度単位） | deg | FlipAngle (0018,1314); Enhanced: MRTimingAndRelatedParametersSequence.FlipAngle | attribute absent in the header, or not an MR object | mr |
| `NumberOfAverages` | 積算回数（加算回数、NSA/NEX） |  | NumberOfAverages (0018,0083); Enhanced: MRAveragesSequence.NumberOfAverages | attribute absent in the header, or not an MR object | mr |
| `MagneticFieldStrength_T` | 静磁場強度（テスラ単位） | T | MagneticFieldStrength (0018,0087) | attribute absent in the header, or not an MR object | mr |
| `ScanningSequence` | スキャンシーケンス種別（SE, GE, IR, EPなど） |  | ScanningSequence (0018,0020) | attribute absent in the header, or not an MR object | mr |
| `SequenceVariant` | シーケンス変異型（SK, SP, SS, MTCなど） |  | SequenceVariant (0018,0021) | attribute absent in the header, or not an MR object | mr |
| `SequenceName` | シーケンス名（メーカーまたはユーザー定義） |  | SequenceName (0018,0024); Philips fallback: private sequence (2005,140F)[0].PulseSequenceName | attribute absent in the header, or not an MR object | mr |
| `InversionTime_ms` | 反転時間（TI、180度パルスからの経過時間、ms単位） | ms | InversionTime (0018,0082); Enhanced: MRModifierSequence.InversionTimes | attribute absent in the header, or not an MR object | mr |
| `EchoNumbers` | シーケンス内のエコー番号 |  | EchoNumbers (0018,0086) | attribute absent in the header, or not an MR object | mr |
| `AcquisitionMatrix` | 収集マトリクスサイズ（周波数・位相エンコードステップ数） |  | AcquisitionMatrix (0018,1310) | attribute absent in the header, or not an MR object | mr |
| `NumberOfPhaseEncodingSteps` | 位相エンコードステップ総数 |  | NumberOfPhaseEncodingSteps (0018,0089) | attribute absent in the header, or not an MR object | mr |
| `PercentSampling` | サンプリング率（収集マトリクスの収集割合、パーセント） | % | PercentSampling (0018,0093) | attribute absent in the header, or not an MR object | mr |
| `PercentPhaseFOV` | 位相エンコード方向視野比率（Percent Phase FOV、パーセント） | % | PercentPhaseFieldOfView (0018,0094) | attribute absent in the header, or not an MR object | mr |
| `ParallelReductionFactorInPlane` | 面内パラレルイメージング高速化倍速数（短縮係数） |  | ParallelReductionFactorInPlane (0018,9069); Enhanced: MRModifierSequence.ParallelReductionFactorInPlane; Siemens fallback: sPat.lAccelFactPE | attribute absent in the header, or not an MR object | mr |
| `SAR` | 全身比吸収率（SAR、W/kg） | W/kg | SAR (0018,1316) | attribute absent in the header, or not an MR object | mr |
| `InPlanePhaseEncodingDirection` | 画像行・列に対する面内位相エンコード方向（ROW, COL, またはCOLUMN） |  | InPlanePhaseEncodingDirection (0018,1312); Enhanced: MRFOVGeometrySequence.InPlanePhaseEncodingDirection | attribute absent in the header, or not an MR object | mr |
| `PhaseEncodingDirectionPatient` | 患者座標系における位相エンコード方向の主軸矢印（A→P, P→A, R→L, L→R, F→H, H→Fなど。フレーム間で変動する場合は\|連結） |  | derived: patient-relative cardinal axis calculated from InPlanePhaseEncodingDirection and ImageOrientationPatient | attribute absent in the header, orientation invalid, or not an MR object | mr |
| `ReceiveCoilName` | 使用された受信コイル名 |  | ReceiveCoilName (0018,1250) | attribute absent in the header, or not an MR object | mr |
| `MRAcquisitionType` | MR収集技術種別（2Dまたは3D） |  | MRAcquisitionType (0018,0023) | attribute absent in the header, or not an MR object | mr |
| `SiemensChannelMixing` | シーメンス固有チャンネルミキシング設定 |  | Siemens private tag (0021,1176) | attribute absent in the header, or Manufacturer does not contain 'siemens' | mr |
| `SiemensCoilElement` | シーメンス固有コイルエレメント識別子 |  | Siemens private tag (0021,114F) | attribute absent in the header, or Manufacturer does not contain 'siemens' | mr |
| `CoilElementCount` | シリーズ内で使用された固有コイルエレメント数 |  | derived: number of unique SiemensCoilElement values in the series | not a Siemens MR series, or no coil elements found in series | mr |
| `CoilElements` | シリーズ内の固有コイルエレメント一覧（\|区切り） |  | derived: unique SiemensCoilElement values in the series joined by \| | not a Siemens MR series, or no coil elements found in series | mr |
| `SiemensIceDims` | シーメンス固有ICE次元文字列（例: CH_ECHO） |  | Siemens private tag (0021,118E) | attribute absent in the header, or Manufacturer does not contain 'siemens' | mr |
| `SiemensIceDimChannel` | SiemensIceDimsから抽出されたチャンネル次元番号 |  | derived: first component of SiemensIceDims (0021,118E) | SiemensIceDims absent, or Manufacturer does not contain 'siemens' | mr |
| `SiemensIceDimEcho` | SiemensIceDimsから抽出されたエコー次元番号 |  | derived: second component of SiemensIceDims (0021,118E) | SiemensIceDims absent or lacks echo index, or Manufacturer does not contain 'siemens' | mr |
| `KVP_kV` | X線管電圧（ピーク管電圧、kV単位） | kV | KVP (0018,0060) | attribute absent in the header, or not a CT/XA object | ct, xa |
| `XRayTubeCurrent_mA` | X線管電流（mA単位） | mA | XRayTubeCurrent (0018,1151) | attribute absent in the header, or not a CT/XA object | ct, xa |
| `ExposureTime_ms` | X線照射時間（露光時間、ms単位） | ms | ExposureTime (0018,1150) | attribute absent in the header, or not a CT/XA object | ct, xa |
| `ConvolutionKernel` | 再構成フィルタ関数（再構成関数／再構成カーネル名） |  | ConvolutionKernel (0018,1210) | attribute absent in the header, or not a CT object | ct |
| `ReconstructionDiameter_mm` | 再構成視野直径（再構成FOV、mm単位） | mm | ReconstructionDiameter (0018,1100) | attribute absent in the header, or not a CT object | ct |
| `TransducerData` | トランスデューサ（超音波プローブ）情報 |  | TransducerData (0018,5010) | attribute absent in the header, or not an US object | us |
| `TransducerType` | 超音波トランスデューサ種別（SECTOR, LINEAR等） |  | TransducerType (0018,6031) | attribute absent in the header, or not an US object | us |
| `MechanicalIndex` | 超音波メカニカルインデックス（MI、音響出力指標） |  | MechanicalIndex (0018,5022) | attribute absent in the header, or not an US object | us |
| `SoftTissueThermalIndex` | 軟部組織サーマルインデックス（TIS、音響出力指標） |  | SoftTissueThermalIndex (0018,5027) | attribute absent in the header, or not an US object | us |
| `BoneThermalIndex` | 骨サーマルインデックス（TIB、音響出力指標） |  | BoneThermalIndex (0018,5024) | attribute absent in the header, or not an US object | us |
| `CranialThermalIndex` | 頭蓋骨サーマルインデックス（TIC、音響出力指標） |  | CranialThermalIndex (0018,5026) | attribute absent in the header, or not an US object | us |
| `UltrasoundColorDataPresent` | 超音波画像にカラーデータが含まれるかどうかのフラグ |  | UltrasoundColorDataPresent (0028,0014) | attribute absent in the header, or not an US object | us |
| `FrameTime_ms` | 1フレームあたりの公称時間（フレーム時間、ms単位） | ms | FrameTime (0018,1063) | attribute absent in the header, or not an XA object | xa |
| `DistanceSourceToDetector_mm` | X線管球焦点から検出器までの距離（SID、mm単位） | mm | DistanceSourceToDetector (0018,1110) | attribute absent in the header, or not an XA object | xa |
| `DistanceSourceToPatient_mm` | X線管球焦点からアイソセンタ／患者までの距離（SOD、mm単位） | mm | DistanceSourceToPatient (0018,1111) | attribute absent in the header, or not an XA object | xa |
| `Radiopharmaceutical` | 投与された放射性医薬品名 |  | RadiopharmaceuticalInformationSequence[0].Radiopharmaceutical (0018,0031) | sequence absent in the header, or not a PT object | pt |
| `RadionuclideTotalDose_Bq` | 放射性核種の総投与放射能（ベクレル、Bq単位） | Bq | RadiopharmaceuticalInformationSequence[0].RadionuclideTotalDose (0018,1074) | sequence absent in the header, or not a PT object | pt |
| `RadionuclideHalfLife_s` | 放射性核種の物理学的半減期（秒単位） | s | RadiopharmaceuticalInformationSequence[0].RadionuclideHalfLife (0018,1075) | sequence absent in the header, or not a PT object | pt |
| `DecayCorrection` | 放射壊変補正の種別（NONE, START, ADMIN等） |  | DecayCorrection (0054,1102) | attribute absent in the header, or not a PT object | pt |
| `Status` | 候補ファイルの処理結果ステータス（organized, listed, planned, skipped, not_processed） |  | organizer: processing outcome status | never missing (always populated with processing status) | 共通 |
| `Reason` | スキップ・未配置または重複衝突の理由コード |  | organizer: skip, unplaced, or duplicate reason code | file is normally organized or listed without conflicts | 共通 |
| `Detail` | ステータスまたは衝突に関する追加の英語詳細説明 |  | organizer: additional explanation or conflict detail | no additional detail is applicable | 共通 |
| `DuplicateOf` | 同一SOPInstanceUIDまたは同一内容を持つ最初に走査されたファイルのPOSIX相対パス |  | organizer: relative path of first-encountered file with same SOPInstanceUID or identical content | file is not a duplicate of another file | 共通 |
| `SizeBytes` | ファイルサイズ（バイト単位） | bytes | organizer: file size in bytes from filesystem | file could not be read or does not exist | 共通 |
| `SHA256` | ファイル内容のSHA-256ハッシュダイジェスト |  | organizer: SHA-256 hex digest of file contents | checksum not requested via --checksum and file not involved in duplicate comparison | 共通 |
