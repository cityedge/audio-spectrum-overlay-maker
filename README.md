# Audio Spectrum Overlay Maker v1.1.2 (setup fix)

Audio Spectrum Overlay Maker is a local Python/Tkinter application for generating silent MP4 spectrum-analyzer overlay videos from audio files. It is designed for music videos, album artwork videos, lyric videos, and long-form YouTube workflows.

Audio Spectrum Overlay Maker は、音源ファイルを解析して、音に反応するスペアナ風オーバーレイ動画を生成するローカルアプリです。標準の黒背景＋白バー素材に加え、動画編集ソフトで安定して合成するための **比較合成用ペア出力** に対応しています。

## Key features

- Generate silent MP4 spectrum overlay videos from WAV / MP3 / M4A / FLAC and other ffmpeg-readable audio files.
- Single-sided and dual-sided horizontal bar spectrum display.
- Integer band-rotation scrolling for a clear moving-spectrum feel.
- Two-color vertical gradient and band gradient modes.
- In-app still preview and actual-audio motion preview.
- 30-second preview render and full-length render.
- Optional pair output for video editors:
  - Main video: normal spectrum material.
  - Matte video: white background + black spectrum shape for Compare/Darken compositing.
- No-overwrite output naming, including paired main/matte filenames.
- System presets and user presets.
- Japanese / English UI.
- Windows helper scripts: `setup.bat` and `start.bat`.

## Why pair output matters

MP4 does not provide a practical true-alpha overlay workflow for this use case. A simple black-background overlay works well with Compare/Lighten for white bars, but colored bars and bright backgrounds can be harder to composite cleanly.

v1.1.1 adds pair output:

```text
1. Put your completed base video on the timeline.
2. Put the matte video above it and set blend mode to Compare/Darken.
3. Put the main spectrum video above the matte and set blend mode to Compare/Lighten.
```

The matte video is generated from the same analyzed bar values as the main video, so timing, bar height, scrolling, and shape match frame-by-frame.

## Requirements

- Python 3.10 or later. On Windows, `setup.bat` uses the Python Launcher as `py -3`, so `py -3` must resolve to Python 3.10+.
- `ffmpeg` and `ffprobe` available either in the app-side `bin` folder or in PATH.
- Python packages listed in `requirements.txt`.
- Tkinter GUI environment.

## Windows quick start

1. Install Python 3.10+ and confirm `py -3 --version` reports Python 3.10 or later.
2. Install ffmpeg and either place `ffmpeg` / `ffprobe` in the app-side `bin` folder or make them available in PATH.
3. Double-click `setup.bat` once.
4. Double-click `start.bat` to launch.

`start.bat` will run `setup.bat` automatically if `.venv` is missing.

Manual launch:

```bat
py -3 app.py
```

## Basic workflow

1. Choose an audio file.
2. Choose an output folder.
3. Select or adjust a preset.
4. Use Visual Preview and Motion Preview.
5. Generate a 30-second preview video.
6. Generate the full video.
7. For cleaner compositing, enable `比較合成用マットも出力` / `Also output matte pair` before rendering.

## Output naming

Normal output:

```text
song_spectrum_720x280_24bars_bw62_r18.mp4
```

Pair output:

```text
song_spectrum_720x280_24bars_bw62_r18.mp4
song_spectrum_720x280_24bars_bw62_r18_matte_dark.mp4
```

If either the main video or the matte video already exists, both names advance together:

```text
song_spectrum_720x280_24bars_bw62_r18 (1).mp4
song_spectrum_720x280_24bars_bw62_r18 (1)_matte_dark.mp4
```

## Files

- `app.py` — GUI application.
- `spectrum_engine.py` — compatibility facade for engine APIs.
- `spectrum_types.py` — shared dataclasses and version.
- `spectrum_audio.py` — ffmpeg/ffprobe and audio decoding.
- `spectrum_analysis.py` — FFT analysis and SpectrumData generation.
- `spectrum_motion.py` — Dynamic motion shaping.
- `spectrum_transform.py` — display-value transformation and integer scrolling.
- `spectrum_parts.py` — visual bar-spectrum part.
- `spectrum_primitives.py` — low-level primitive renderer.
- `spectrum_draw.py` — drawing facade.
- `spectrum_encoder.py` — MP4 encoder pipe.
- `spectrum_workflow.py` — preview/full render workflows and pair output.
- `preset_manager.py` — system/user presets.
- `ui_tooltips.py` — tooltip helper.
- `USER_GUIDE.md` — operation guide.
- `CHANGELOG.md` — version history.
- `DEVELOPMENT_NOTES.md` — architecture notes.
- `TEST_REPORT.md` — release test notes.
- `LICENSE` — MIT License.

## Privacy

The app runs locally. Audio files are decoded by your local ffmpeg. This application does not upload your files.

## License

MIT License. See `LICENSE`.


## ffmpeg / ffprobe lookup

The app looks for ffmpeg and ffprobe in this order:

1. `bin` subfolder next to the app files or EXE
   - Windows examples:
     - `bin\ffmpeg.exe`
     - `bin\ffprobe.exe`
2. System PATH

This makes PyInstaller-style EXE distribution easier: you may place the ffmpeg binaries in a sibling `bin` folder next to the EXE without modifying PATH.
