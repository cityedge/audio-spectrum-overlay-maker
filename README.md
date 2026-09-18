# Audio Spectrum Overlay Maker v1.4.1

Audio Spectrum Overlay Maker is a local Windows Python/Tkinter application for generating silent MP4 spectrum-analyzer overlay videos from audio files.

Audio Spectrum Overlay Maker は、音源ファイルを解析して、音に反応するスペアナ風オーバーレイ動画を生成するローカルアプリです。動画編集ソフトで背景映像や字幕動画に重ねるための素材作成を目的にしています。

## Main Features

v1.4.1 はデジタル描画を大幅に高速化しました。設定変更は不要で、プレビュー、メイン動画、マット動画に自動適用されます。見た目とピークホールドの仕様は維持しています。

Digital rendering now caches segment shapes and colors. In a 720×280, 96-bar, 64-segment test with combined effects, a two-second main/matte MP4 pair took 2.41 seconds instead of 19.70 seconds. Results depend on settings and hardware; see `TEST_REPORT.md` for conditions. High-frequency boost is also reflected in the still preview.

- Silent MP4 spectrum overlay generation from WAV / MP3 / M4A / FLAC and other ffmpeg-readable audio files.
- Single-sided and dual-sided bar display.
- Digital / LED-style segmented bars.
- Optional one-pixel edge glow for black-background main output.
- Display-only high-frequency boost for balancing low-heavy spectrum material.
- Peak hold modes with configurable hold and decay: markers, peaks only, or held peaks as bars.
- Visible bar counts through 128, with matching Advanced Custom internal-analysis choices.
- Band scrolling with vertical, band, and loop-band gradients.
- Post Transform layer applied after each frame is drawn.
- Static rotation, vertical trapezoid, horizontal trapezoid, and combined transforms.
- Audio-reactive scaling with peak-hold style envelope, threshold, ceiling, and optional low-band-only detection.
- In-app still preview.
- 2-second and 10-second in-app motion previews for quick checks.
- 30-second preview MP4 and full-length render.
- Render cancellation with optional retention of playable partial videos.
- Optional main/matte pair output for Compare/Lighten + Compare/Darken compositing.
- Parallel main/matte rendering when pair output is enabled.
- SRT Spectrum Video Composer handoff through `final_composer.py`.
- System presets and user presets.
- Japanese / English UI.

## Typical Workflow

1. Select an audio file.
2. Select an output folder.
3. Choose a system preset or adjust the settings.
4. Check the still preview.
5. Use `2秒プレビュー` for quick motion checks, or `10秒プレビュー` for a longer check.
6. Generate a 30-second preview MP4 and test compositing in your video editor.
7. Generate the full-length spectrum video.
8. If needed, open SRT Spectrum Video Composer and create the final video there.

## Pair Output

MP4 does not provide a practical true-alpha workflow for this use case. Audio Spectrum Overlay Maker therefore supports paired output:

```text
Main video:
  black background + normal spectrum material

Matte video:
  white background + black spectrum shape
```

Recommended editor stacking:

```text
Bottom: finished background video
Middle: matte video  -> Compare/Darken
Top:    main video   -> Compare/Lighten
```

The main and matte videos are generated from the same analyzed values and the same Post Transform settings. Bar height, peak hold, scrolling, rotation, trapezoid transforms, and audio-reactive scaling stay frame-aligned.

When pair output is enabled, the main and matte videos render in parallel. Digital drawing is accelerated in v1.4.1; Post Transform and encoding still contribute to total rendering time.

## Post Transform Layer

Post Transform is a coordinate-mapping layer applied after a complete RGB frame has already been drawn.

```text
audio analysis
dynamic motion shaping
basic drawing
Post Transform
ffmpeg encoding
```

Supported transforms in v1.4.1:

- Rotation around the canvas center.
- Vertical trapezoid: negative values narrow the top, positive values narrow the bottom.
- Horizontal trapezoid: negative values narrow the left side, positive values narrow the right side.
- Combined trapezoid + rotation.
- Audio-reactive scaling.

The canvas size is preserved. Out-of-canvas areas are clipped. Newly exposed areas are filled with black for the main video and white for the matte video.

## Audio-Reactive Scaling

Audio-reactive scaling is controlled by the `音量連動の拡大` / `Audio reactive scale` checkbox.

- Default: OFF.
- Scale range: 80% to 150%.
- 100% is neutral.
- Values above 100% enlarge on louder input.
- Values below 100% shrink on louder input.
- The envelope uses peak-hold style hold/decay settings.
- The start threshold and ceiling control how easily the maximum scale is reached.
- Low-band-only detection is ON by default, so kick and bass energy can drive the pulse more naturally.

The low-band reference range is configured in the Advanced tab. The default is 25% of the low-frequency side of the spectrum bars.

## High-Frequency Boost

High-frequency boost is a display correction for sources where low bands dominate and high bands rarely rise. It adds a configurable dB slope across the analyzed frequency range before the display values are generated.

- Range: 0 dB to 36 dB.
- Curve: Gentle, Standard, Moderately Steep, or Steep. The steeper curves are intentionally weighted toward the upper end so mid bands do not rise too much.
- 0 dB disables the correction.
- The correction affects the drawn spectrum and peak hold.
- Audio-reactive scaling uses the unboosted values, so visual balancing does not change the pulse trigger.

## Edge Glow

Edge Glow is a black-background-only drawing option for the main video. It spreads the already rendered spectrum colors by one pixel, then places the original frame back on top. This can soften visible compression/compositing outlines around digital pieces, rounded bars, and peak-hold fragments.

- Default: None.
- Light: four directions, fixed 12.5% strength.
- Standard: four directions, fixed 25% strength.
- Strong: four directions, fixed 50% strength.
- Matte output is unchanged.
- Edge Glow is applied before Post Transform, so rotation and trapezoid transforms carry the glow with the spectrum.

## Render Cancellation

Both 30-second preview rendering and full rendering can be cancelled.

- Default behavior removes incomplete main/matte MP4 files.
- The Advanced-tab `Keep Partial Videos on Cancel` option instead closes each active encoder normally and keeps its playable partial MP4.
- Kept main/matte files can have different durations because each encoder stops at its own next frame boundary. They are for visual inspection only, not a compositing-ready pair.

## Visible Bar Counts

Visible bar choices are `18`, `24`, `32`, `48`, `64`, `80`, `96`, `112`, and `128`. The 80-128 choices are intended for higher-density output, especially at 720px width or larger.

In Advanced Custom mode, the internal-analysis choices mirror the visible choices. Matching both values gives one analysis band per visible bar.

## System Presets

v1.4.1 includes these system presets:

1. `01 Basic White`
2. `02 Dual White`
3. `03 Blue Gradient`
4. `04 Neon Dual`
5. `05 Scrolling Spectrum`
6. `06 Smooth Ambient`
7. `07 Digital LED`
8. `08 Digital Dual`
9. `09 Digital Neon Scroll`
10. `10 Trapezoid Neon`
11. `11 Vertical Scroll`
12. `12 Pulsating LED Scroll`

User presets are stored separately in `presets_user.json`. That file is intentionally ignored by Git.

## Requirements

- Windows 10 / 11.
- Python 3.10 or later.
- Python Launcher `py`.
- `ffmpeg` and `ffprobe`.
- Python packages in `requirements.txt`.

`ffmpeg` and `ffprobe` are searched in this order:

1. `bin` folder next to the app files or packaged EXE.
2. System PATH.

The release package includes `bin\README.txt`; place `ffmpeg.exe` and `ffprobe.exe` there if you do not want to modify PATH.

## Quick Start

1. Extract the release zip.
2. Put `ffmpeg.exe` and `ffprobe.exe` in `bin`, or make them available in PATH.
3. Double-click `setup.bat`.
4. Double-click `start.bat`.

Manual launch after setup:

```bat
.venv\Scripts\python.exe app.py
```

## SRT Spectrum Video Composer

`final_composer.py` is bundled as SRT Spectrum Video Composer. Audio Spectrum Overlay Maker can launch it through the `SRT Spectrum Video Composer を開く` button and pass:

- source audio path
- generated main spectrum video path
- generated matte video path

Background image, SRT subtitles, final output path, and layout are selected on the composer side.

## Package Contents

The source release zip is based on the v1.3-alpha1 package layout and includes:

- `app.py`
- `final_composer.py`
- `preset_manager.py`
- `spectrum_*.py`
- `ui_tooltips.py`
- `requirements.txt`
- `setup.bat`
- `start.bat`
- `README.md`
- `USER_GUIDE.md`
- `USER_MANUAL_SSVC.md`
- `CHANGELOG.md`
- `DEVELOPMENT_NOTES.md`
- `DEVELOPMENT_REVIEW.md`
- `TEST_REPORT.md`
- `RELEASE_NOTES.md`
- `LICENSE`
- `.gitignore`
- `bin\README.txt`

Generated videos, local virtual environments, user presets, caches, and ffmpeg binaries are not included.

## Privacy

The app runs locally. Audio files are decoded by your local ffmpeg. This application does not upload your files.

## License

MIT License. See `LICENSE`.
