# v1.3.2 Test Report

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
- UI text import check: passed
  - reset labels exist in Japanese and English
- Release package file list check: passed
  - package: `output/audio_spectrum_overlay_maker_v1_3_2.zip`
  - entries: 33
  - no `.venv`, `output`, `work`, `tests`, `__pycache__`, generated MP4, user preset, or ffmpeg executable entries

## Manual / User-Confirmed Checks

- Static rotation: confirmed working.
- Vertical/horizontal trapezoid: confirmed working.
- Combined trapezoid + rotation: confirmed working after homography-based ordering fix.
- Audio-reactive scaling: confirmed working and improved after peak-hold style envelope plus threshold/ceiling tuning.
- Low-band-driven pulse direction: design accepted for v1.3.2.
- Main/matte parallel render: confirmed working by user with SSVC compositing.

## ffmpeg / ffprobe Lookup Order

1. App-side `bin` folder
2. PATH fallback

## Notes

Heavy combinations of digital bars, scrolling, peak hold, rotation, trapezoid, audio-reactive scaling, edge glow, high-frequency boost, and matte output are expected to render slowly. This is accepted for v1.3.2 because Post Transform flexibility and visual tuning are the priority.
