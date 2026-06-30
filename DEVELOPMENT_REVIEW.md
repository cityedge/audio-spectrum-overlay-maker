# Audio Spectrum Overlay Maker v1.3.1 Release Review

## Scope

v1.3.1 stabilizes the edge-glow polish pass on top of the v1.3 Post Transform release. The reviewed scope is:

- peak-hold drawing
- digital segmented bars
- scrolling and gradients
- Post Transform layer
- rotation / vertical trapezoid / horizontal trapezoid
- audio-reactive scaling
- edge glow
- main/matte pair output
- SRT Spectrum Video Composer handoff
- system presets
- release packaging

## Findings

No release-blocking defect was found in the reviewed code paths.

The important behavioral contracts are preserved:

- No-transform settings resolve to identity Post Transform.
- Audio-reactive scaling is disabled unless the explicit checkbox is ON.
- Audio-reactive scale `100%` remains neutral.
- Audio-reactive scale values below `100%` shrink instead of enlarge.
- Edge Glow is applied only to black-background main output and is disabled for matte output.
- Edge Glow is automatically disabled when the detailed background color is not black.
- Main and matte outputs use the same transformed frame geometry.
- Pair output keeps no-overwrite filename pairing.
- `final_composer.py` is not imported during normal app startup.
- User presets remain outside the release package.

## Design Notes

Post Transform is correctly kept after complete frame drawing. Rotation, trapezoid, and scale are not embedded into the bar drawing layer. This keeps the drawing pipeline understandable and preserves compatibility with digital bars, peak hold, gradients, and matte output.

Audio-reactive scaling is intentionally implemented as a Post Transform parameter driven by per-frame bar values. The low-band-only option uses the low-frequency side of the already transformed display bars, which is practical for kick/bass-driven pulse effects.

Edge Glow is a drawing-stage main-output effect, applied before Post Transform. It spreads the rendered spectrum color by one pixel in eight directions and restores the original frame on top. This keeps the matte geometry unchanged while reducing visible compression/compositing outlines around digital pieces, rounded bars, and peak-hold fragments.

Main and matte rendering now runs in parallel when pair output is enabled. Both renders receive the same `bar_values`, `peak_values`, `TransformSettings`, and `PostTransformSettings`, so the geometry contract is preserved.

## Residual Risks

- Heavy Post Transform combinations are CPU-bound and can be slow.
- GUI layout should still be visually checked on the target Windows environment before publishing screenshots.
- The app depends on a local ffmpeg / ffprobe installation or binaries placed in `bin`.

## Release Decision

Proceed with v1.3.1 packaging.
