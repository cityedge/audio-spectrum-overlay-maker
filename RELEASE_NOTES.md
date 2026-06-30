# Audio Spectrum Overlay Maker v1.3.1 Release Notes

v1.3.1 is the edge-glow polish release on top of the Post Transform generation.

## Highlights

- Post Transform layer is now part of the main workflow.
- Edge Glow can be enabled for black-background main output to soften visible compression/compositing outlines.
- Static rotation, vertical trapezoid, horizontal trapezoid, and combined transforms are available from the Visual tab.
- Audio-reactive scaling can pulse or shrink the whole spectrum based on volume.
- Low-band-only detection is available for audio-reactive scaling, making kick and bass-driven pulse effects easier to tune.
- Peak hold, digital bars, scrolling, gradients, and pair output all work through the same render pipeline.
- Main and matte pair output can render in parallel.
- Motion preview now has 2-second and 10-second buttons.
- Bundled SRT Spectrum Video Composer files have been refreshed without changing the Audio Spectrum Overlay Maker handoff interface.
- System presets now include:
  - `10 Trapezoid Neon`
  - `11 Vertical Scroll`
  - `12 Pulsating LED Scroll`

## Compatibility Notes

- Existing no-transform settings continue to behave as identity Post Transform.
- Main and matte videos use the same Post Transform settings.
- The canvas size is preserved; out-of-canvas transformed areas are clipped.
- Newly exposed areas are black in the main video and white in the matte video.
- `presets_user.json` remains a local user file and is not included in the release zip.
- `ffmpeg.exe` and `ffprobe.exe` are not included in the release zip; only `bin\README.txt` is included.

## Known Cost

Post Transform effects are intentionally flexible and can be CPU-heavy. Heavy combinations such as digital bars, scrolling, peak hold, trapezoid, rotation, audio-reactive scaling, and matte pair output can take longer than real time to render.
