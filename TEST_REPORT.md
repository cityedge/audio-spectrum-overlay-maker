# v1.3.0 Test Report

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
- UI text import check: passed
  - reset labels exist in Japanese and English
- Release package file list check: passed
  - package: `output/audio_spectrum_overlay_maker_v1_3_0.zip`
  - entries: 33
  - no `.venv`, `output`, `work`, `tests`, `__pycache__`, generated MP4, user preset, or ffmpeg executable entries

## Manual / User-Confirmed Checks

- Static rotation: confirmed working.
- Vertical/horizontal trapezoid: confirmed working.
- Combined trapezoid + rotation: confirmed working after homography-based ordering fix.
- Audio-reactive scaling: confirmed working and improved after peak-hold style envelope plus threshold/ceiling tuning.
- Low-band-driven pulse direction: design accepted for v1.3.0.
- Main/matte parallel render: confirmed working by user with SSVC compositing.

## ffmpeg / ffprobe Lookup Order

1. App-side `bin` folder
2. PATH fallback

## Notes

Heavy combinations of digital bars, scrolling, peak hold, rotation, trapezoid, audio-reactive scaling, and matte output are expected to render slowly. This is accepted for v1.3.0 because Post Transform flexibility is the priority.
