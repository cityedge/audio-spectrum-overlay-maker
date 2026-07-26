# Audio Spectrum Overlay Maker v1.4.0 Release Notes

v1.4.0 is the spectrum-density and render-control release. It completes the peak-hold display expansion and adds practical control for long or expensive renders.

## Highlights

- Peak Hold is a display mode dropdown: Off, Peak Markers, Peaks Only, or Peaks as Bars.
- Visible bar counts now reach 128, with 80, 96, and 112 available between 64 and 128.
- Advanced Custom internal-analysis choices now mirror visible bar choices, so 80/96/112/128 can use one analysis band per visible bar.
- Preview-video and full-video rendering can be cancelled from the main action area.
- Default cancellation removes incomplete main and matte MP4 files.
- Advanced `Keep Partial Videos on Cancel` finalizes and retains playable partial MP4s for visual inspection.

## Partial Video Compatibility

When partial-video retention is enabled with pair output, main and matte encoders stop independently. Their durations can differ, so retained files are not a compositing-ready main/matte pair. Full renders that complete normally retain the usual frame-alignment guarantee.

## Existing v1.3.x Features

v1.4.0 continues to include the Post Transform layer, rotation, vertical/horizontal trapezoid transforms, audio-reactive scaling, edge glow, high-frequency boost, scrolling, digital bars, parallel main/matte output, and SRT Spectrum Video Composer handoff.

## Packaging Notes

- `ffmpeg.exe` and `ffprobe.exe` are not included in the source release zip; only `bin\README.txt` is included.
- `final_composer.py` and `USER_MANUAL_SSVC.md` are included without changing the handoff interface.
- PyInstaller EXE builds are produced separately from the source release package.
