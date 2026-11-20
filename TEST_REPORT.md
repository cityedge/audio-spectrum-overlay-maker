# v1.5.0 Test Report

## v1.5.0 リリース検証（2026-11-18）

- プロジェクト内の `.venv\Scripts\python.exe`（Python 3.10.6）を使用。
- `tests/test_composer_handoff.py`：10テスト成功。実スレッドでのMP4生成、連番、設定変更、失敗・キャンセル、SSVC v1.1.1へのJSON受け渡しを含む。
- `tests/test_opacity_export.py`：7テスト成功。不透明度の数値検証、実MP4ペア、白PNG、キャンセル・失敗時の抑止を含む。
- `tests/test_output_canvas.py`：5テスト成功。9配置・オフセット・クリップ・無効値と、1920×1080のプレビュー／全体生成ペアを検証。
- `tests/test_digital_renderer.py`：4テスト成功。既存の高速描画と互換経路の画素一致を確認。
- `tests/test_opacity_ui.py` と `tests/test_output_canvas_ui.py`：ともに成功。整数スライダー、日英表示、プリセット、プレビュー、入力検証を確認。
- 合計26テスト＋2種類のTk UIテストが成功。今回の実行ではPyInstallerビルドやPowerDirectorの操作は行っていない。
- 配布ZIPは `output/audio_spectrum_overlay_maker_v1_5_0.zip`、37ファイル。v1.4.1の35ファイルに `spectrum_opacity.py` と `spectrum_output_canvas.py` を追加。
- アーカイブのCRC、ワークスペースとの全ファイル一致、Python構文、UTF-8文書、展開先からの独立import・GUIタイトル・初期値を検証。メーカーv1.5.0、SSVC v1.1.1を確認。
- `.venv`、生成動画、ユーザープリセット、テスト、作業フォルダ、FFmpeg/FFprobe実行ファイル、EXE、README_SSVC.mdは同梱しない。SHA-256ファイルを別途作成。

再実行はプロジェクトルートで `where.exe python` と `.\.venv\Scripts\python.exe --version` を確認したうえで、上記各テストを `.\.venv\Scripts\python.exe -B tests/<ファイル名>` で実行する。

## SSVC半透明連携の開発版検証（2026-11-18）

- `tests/test_composer_handoff.py`：10テスト成功。schema_version 1の互換性、任意の `spectrum_asset`、不透明度0／1／50／99／100%、不正値拒否、未生成・ファイル欠落時の動作を検証。
- 正常生成した動画・マット・元音源・不透明度を一組で保持。生成中や生成後に設定を変更しても混在せず、失敗・キャンセル（途中動画を残す場合も含む）で直前の成功結果が置き換わらないことを確認。
- 実際のTk描画スレッドで0.5秒のメイン／マットMP4を生成。同名ファイルを保持したまま連番を付け、その実際の出力パスを連携JSONに記録することを確認。
- 同梱SSVC v1.1.1の非表示Tk画面に実際の生成JSONを渡し、ファイル名が任意でも0／50／99%は半透明・乗算＋加算・追加透明度0、100%は従来素材として受信することを確認。
- 通常のメーカー起動時にはSSVCをimportしないことを別Pythonプロセスで検証。SSVC起動ボタンのテストでは子プロセス起動をモックし、コマンドとJSONを確認。EXE版の実起動は未検証。
- 既存の `tests/test_opacity_export.py`（7テスト）と `tests/test_opacity_ui.py` も成功。
- 新規テストの生成物は `output/composer_handoff_checks/`。ユーザー更新済みのSSVC本体とマニュアルは変更していない。公開ZIP・EXEは今回更新していない。

## 不透明度・白PNGの開発版検証（2026-11-17）

- `tests/test_opacity_export.py`：7テスト成功。全256階調×不透明度0～100%、100%パススルー、0%の黒／白、半透明時の背景・グロー処理、通常／デジタル＋変形後のDifference合成式、市松プレビューを検証。
- 実際のプレビュー／全体生成、単独／ペア出力、不透明度0／50／100%を確認。MP4のフレーム数・寸法・画素値を検証。50%素材の境界にはH.264圧縮によるオーバーシュートがあり、エンコード後の画素検証はその誤差を許容。
- 白PNGはRGB形式・全画素255。通常サイズ768×120と全画面1920×1080、ON/OFF、同名ファイルの保持、キャンセル／失敗時に生成されないことを検証。
- `tests/test_opacity_ui.py`：初期値、プリセット保存、日英ラベル、市松プレビュー、0%時の動きプレビュー、グロー設定の復帰、小数入力拒否を検証。
- 既存のデジタル描画4テスト、キャンバス5テスト、キャンバスUI検証も成功。
- 実ウィンドウの画面確認はユーザーのEsc操作で停止。上記UI検証はTkの自動テストによるもの。PowerDirector上での新しい半透明素材の最終合成確認は未実施。
- 生成物は `output/opacity_checks/`。公開パッケージとEXEは今回更新していない。

## 全画面キャンバス出力の開発版検証（2026-11-17）

- `tests/test_output_canvas.py`：9方向の配置、正負のオフセット、矩形クリップ、完全に領域外の配置、OFF時の同一画像返却、不正サイズ、Post Transform後の配置、メイン黒／マット白の余白を検証。
- 合成音源から768×120の96本デジタルスペアナを1920×1080へ配置し、プレビュー経路と全体生成経路で実際にメイン／マットを並列MP4出力。解像度、30fps、両動画のフレーム数、デコード後の余白色、配置領域内の描画を確認。
- `tests/test_output_canvas_ui.py`：初期値、日英9配置、プリセットの保存・再読み込み、OFF/ONでの値保持、見た目プレビューの寸法、動きプレビューの小サイズ保存／全画面表示、不正入力時の生成阻止を検証。専用プリセットは `output/canvas_checks/` に保存。
- `tests/test_digital_renderer.py`：既存デジタル描画の4テスト成功。
- 実ウィンドウでチェックボックス、見た目タブ最下部の設定、日本語／英語表示、ON時の下中央プレビューを確認。
- PowerDirectorで今回生成したスペアナペアを読み込む最終確認はユーザー側で実施予定。公開ZIP・EXEは今回更新していない。

## デジタル描画高速化の追加検証（2026-09-18）

- デジタル専用描画経路を追加。形状・色・角丸の描画結果をキャッシュし、フレームごとに点灯する小片の行を選択する。
- 通常バーの描画経路は維持。極端に狭いキャンバスでバーが重なる場合も従来の描画経路を使用する。
- 160種類の組み合わせで従来経路と画素単位で完全一致。片側／両側、分割数、角丸、隙間、背景色、グラデーション、スクロール色位置、ガンマ、ピーク表示各モード、グローを含む。
- 点灯境界の丸め、ピークの境界値、メイン／マットの並列描画、Post Transform後の一致を追加確認。自動テスト4件成功。
- 720×280・96バー・64分割の描画単体測定（12フレーム平均、実行環境依存）：片側155.25→1.93ms、両側164.78→1.87ms。初回キャッシュ構築込みは片側6.28ms、両側4.76ms。
- 同サイズの2秒・30fpsのメイン／マット同時MP4出力：19.696→2.410秒。両側デジタル、ピーク片、色スクロール、回転、縦横台形、音量連動拡大、メインの標準グローを併用。音声解析は含めず、固定シードの疑似音量を使用。
- 従来／高速化後のMP4をデコードし、メインとマットそれぞれ全60フレームのハッシュが完全一致。
- ルートのPythonファイルの構文解析およびappのインポート成功。GUI操作による実音源確認は未実施。
- 検証動画：`output/digital_renderer_check/`。ユーザーによる実環境確認で約20倍の高速化が報告された（設定・環境に依存）。

再実行コマンド（開発リポジトリのプロジェクトルート、プロジェクト内のPythonを使用。テストコードは配布ZIP対象外）：

```powershell
where.exe python
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -B tests/test_digital_renderer.py
.\.venv\Scripts\python.exe -B tests/test_digital_renderer.py --benchmark
.\.venv\Scripts\python.exe -B tests/test_digital_renderer.py --encode
```

## v1.4.1までの Automated Checks

- Python version check via project `.venv`: Python 3.10.6
- Python AST parse check: passed for all Python files
- Main app import: passed
- Normal app import does not import `final_composer`: passed
- Preset list check: passed
  - `10 Minimal Lower Bar` removed
  - `10 Trapezoid Neon` present
  - `11 Vertical Scroll` present
  - `12 Pulsating LED Scroll` present
  - no duplicate preset names
- Audio-reactive scale OFF check: passed
  - target scale can be non-100 without activating Post Transform
- Audio-reactive shrink check: passed
  - enabled target scale `80%` resolves to shrink behavior
- Edge Glow check: passed
  - Light Glow: one-pixel four-direction 12.5% spread works on black background
  - Standard Glow: one-pixel four-direction 25% spread works on black background
  - Strong Glow: one-pixel four-direction 50% spread works on black background
  - original pixels are restored on top
  - non-black backgrounds bypass the effect
  - UI disables Edge Glow when the detailed background color is not black
  - Legacy Simple Glow and Advanced Glow values are normalized to Standard Glow
- High-frequency boost check: passed
  - dB slope is 0 dB at the low end and reaches the configured amount at the high end
  - curve exponents are high-end weighted: Gentle = 2, Standard = 4, Moderately Steep = 6, Steep = 8
  - boosted display values rise above unboosted values in high bands
  - audio-reactive scaling can receive unboosted values separately from display values
  - still preview uses synthetic raw dB data, so boost amount and curve are reflected without an audio file
- Peak Hold mode check: passed
  - legacy ON presets normalize to Peak Markers
  - Off disables peak generation
  - Peaks Only draws markers without bar bodies
  - Peaks as Bars draws held peaks as the bar body
- Visible-bar count check: passed
  - visible choices include 80, 96, 112, and 128
  - Advanced Custom internal-analysis choices mirror all visible choices through 128
  - 112 internal bands map directly to 112 visible bands
- Render cancellation check: passed
  - default cancellation removes incomplete main/matte MP4 files
  - keep-partial cancellation finalizes playable main/matte MP4 files independently
  - kept pair durations can differ by design
- UI text import check: passed
  - reset labels exist in Japanese and English
- Release package file list check: passed
  - package: `output/audio_spectrum_overlay_maker_v1_4_1.zip`
  - entries: 35 (v1.4.0 contents plus `spectrum_digital.py`)
  - no `.venv`, `output`, `work`, `tests`, `__pycache__`, generated MP4, user preset, or ffmpeg executable entries

## Manual / User-Confirmed Checks

- Static rotation: confirmed working.
- Vertical/horizontal trapezoid: confirmed working.
- Combined trapezoid + rotation: confirmed working after homography-based ordering fix.
- Audio-reactive scaling: confirmed working and improved after peak-hold style envelope plus threshold/ceiling tuning.
- Low-band-driven pulse direction: confirmed in normal use.
- Main/matte parallel render: confirmed working by user with SSVC compositing.
- Default cancellation and keep-partial cancellation: confirmed by user from the application UI.

## ffmpeg / ffprobe Lookup Order

1. App-side `bin` folder
2. PATH fallback

## Notes

v1.4.1 substantially reduces digital drawing cost. Post Transform, glow, audio analysis, and encoding still contribute to total rendering time. The measured speedups are not guarantees for every source or setting.

## Visible Bar Count

- Visible-bar choices now include 80, 96, 112, and 128. At 128, qualitative settings raise the internal analysis count to 128 so display bands map one-to-one.
- Advanced Custom internal-analysis choices match the visible-bar choices: 18, 24, 32, 48, 64, 80, 96, 112, and 128.
