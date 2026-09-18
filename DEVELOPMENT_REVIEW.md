# Audio Spectrum Overlay Maker v1.4.1 Release Review

## Scope

v1.4.1 adds cached digital rendering and still-preview high-frequency boost reflection. Pixel-equivalence tests cover peak modes, colors, rounding, narrow-canvas fallback, concurrent main/matte rendering, and Post Transform. Decoded main/matte MP4 frames match the reference renderer. The user confirmed a substantial speedup in actual use.

The following v1.4.0 features are retained:

- Peak Hold display modes: Peak Markers, Peaks Only, and Peaks as Bars.
- Render cancellation for preview-video and full-video rendering.
- Optional preservation of finalized partial videos on cancellation.
- Visible-bar choices through 128.
- Matching Advanced Custom internal-analysis choices through 128.

## Findings

No release-blocking defect was found in the reviewed paths.

The important behavioral contracts are preserved:

- Normal main/matte renders receive identical analysis values, peak values, and Post Transform settings.
- Full renders that complete normally remain frame-aligned for compositing.
- Default cancellation terminates active encoders and removes incomplete outputs.
- Keep-partial cancellation closes each active encoder normally, leaving playable partial MP4 files when encoding has started.
- Kept main/matte partial files can have different durations and are documented as inspection-only artifacts.
- Visible 80/96/112/128 choices remain within the existing analysis, transform, drawing, and encoding paths.
- Advanced Custom can match internal-analysis and visible-bar counts one-to-one.
- `final_composer.py` is not imported during normal app startup.
- User presets and ffmpeg binaries remain outside the source release package.

## Residual Risks

- Heavy Post Transform combinations remain CPU-bound and can be slow.
- Keep-partial output is intentionally not frame-synchronized between main and matte.
- GUI layout should still be visually checked on the target Windows environment before publishing screenshots or an EXE build.
- The app depends on a local ffmpeg / ffprobe installation or binaries placed in `bin`.

## Release Decision

Proceed with v1.4.1 source packaging. PyInstaller EXE creation is handled separately by the user.
