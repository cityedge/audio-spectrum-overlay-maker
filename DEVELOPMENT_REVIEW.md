# Audio Spectrum Overlay Maker v1.5.0 Release Review

## Scope

v1.5.0 adds full-frame output-canvas placement, matched front/matte opacity, optional white PNG output, and metadata-based handoff to bundled SSVC v1.1.1. The regression suites cover arithmetic, real encoding, UI/preset behavior and the last-successful-render snapshot. Results and commands are recorded in `TEST_REPORT.md`.

Existing features are retained:

- Peak Hold display modes: Peak Markers, Peaks Only, and Peaks as Bars.
- Render cancellation for preview-video and full-video rendering.
- Optional preservation of finalized partial videos on cancellation.
- Visible-bar choices through 128.
- Matching Advanced Custom internal-analysis choices through 128.
- Cached digital rendering and high-frequency boost in the still preview.

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
- Opacity follows Post Transform and precedes output placement. At 100% it passes through unchanged; below 100% the front has black background and no glow.
- Output placement does not resize the source. Main and matte share anchors/offsets with black/white padding respectively.
- White PNG output matches actual video dimensions, follows successful completion only, and does not overwrite existing files.
- Failed/cancelled renders do not replace the immutable handoff snapshot. JSON opacity metadata describes already-applied opacity and is not applied again by SSVC.

The standalone SSVC README described absent files and launch/build instructions for a different project. It is excluded from this bundle; the supplied SSVC code and user manual are preserved unchanged as separate-project deliverables.

## Residual Risks

- Heavy Post Transform combinations remain CPU-bound and can be slow.
- Full-frame output increases transfer and encoding work; CRF does not promise a fixed file size.
- MP4 is lossy and has no native alpha here. Decoded values may differ slightly from the pre-encode opacity formula.
- Difference-based Add substitution requires each component of `F + B*M` to stay at most 1. Extra color correction or front-only glow can break that condition.
- The PowerDirector rectangular-boundary workaround depends on keeping the exported canvas full-frame and aligned in the editor.
- Keep-partial output is intentionally not frame-synchronized between main and matte.
- GUI layout should still be visually checked on the target Windows environment before publishing screenshots or an EXE build.
- The app depends on a local ffmpeg / ffprobe installation or binaries placed in `bin`.

## Release Decision

Proceed with v1.5.0 source packaging: retain the preceding 35-file manifest and add the opacity and output-canvas modules, for 37 files. Verify archive membership and byte equality, then import the extracted application independently of the source tree. SSVC retains its own version 1.1.1. PyInstaller EXE creation is handled separately by the user; GitHub publication is not performed during source packaging.
