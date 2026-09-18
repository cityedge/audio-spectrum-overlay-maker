# v1.4.1 Test Report

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

## Automated Checks

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
