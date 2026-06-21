# Audio Spectrum Overlay Maker v1.0.0

Audio Spectrum Overlay Maker is a local Python/Tkinter application for generating MP4 spectrum-analyzer overlay videos from audio files. It is designed for music videos, album artwork videos, and video-editing workflows where a black-background spectrum overlay is composited on top of artwork.

Audio Spectrum Overlay Maker は、音源ファイルからスペアナ（スペクトラムアナライザー）風のオーバーレイ動画を生成する、ローカル動作の Python/Tkinter アプリです。黒背景＋白バーの MP4 素材を作成し、PowerDirector などの動画編集ソフトで比較（明）/ Lighten / Screen 系の合成に使うことを想定しています。

## Main features

- Generate a black-background MP4 spectrum overlay from WAV / MP3 / M4A and other ffmpeg-readable audio files.
- Output video contains no audio; the audio file is used only for analysis.
- Dynamic spectrum motion designed for visually natural music-video overlays.
- Visible bar count: 18 / 24 / 32 / 48 / 64.
- Internal analysis bands are separated from visible bar count for stable perceived motion.
- Rounded/capsule bars with smooth low-volume emergence.
- In-app visual preview and actual-audio motion preview.
- 30-second preview MP4 generation and full-length rendering.
- Presets with system presets and user presets.
- Qualitative motion controls plus advanced detailed parameters.
- Automatic frequency range analysis, with optional manual frequency range.
- Japanese / English UI switching.
- Automatic no-overwrite output filename handling: `file.mp4`, `file (1).mp4`, `file (2).mp4`, ...

## Requirements

- Windows / macOS / Linux with Python 3.10 or later.
- `ffmpeg` and `ffprobe` available in PATH.
- Python packages listed in `requirements.txt`.

## Windows quick start

On Windows, you can use the included batch files:

1. Double-click `setup.bat` once to create `.venv` and install dependencies.
2. Double-click `start.bat` to launch the app.

`start.bat` will run `setup.bat` automatically if `.venv` does not exist.

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python app.py
```

On Windows, depending on your Python installation:

```bat
py app.py
```

## Files

- `app.py` — GUI application.
- `spectrum_engine.py` — audio analysis and video rendering engine.
- `preset_manager.py` — system/user preset management.
- `ui_tooltips.py` — tooltip helper.
- `requirements.txt` — Python dependencies.
- `setup.bat` — Windows setup helper.
- `start.bat` — Windows launch helper.
- `USER_GUIDE.md` — full operation manual.
- `CHANGELOG.md` — version history.
- `LICENSE` — MIT License.

## Privacy

The app runs locally. Audio files are decoded by your local `ffmpeg`; no file is uploaded by this application.

## License

MIT License. See `LICENSE`.
