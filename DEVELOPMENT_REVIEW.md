# Audio Spectrum Overlay Maker v1.1.1 Release Review

## Scope

v1.1.1 is the stable GitHub publication package. It consolidates the alpha-series work into a practical release centered on MP4 spectrum overlay generation and Compare/Darken matte pair output.

## Stabilized feature set

- Single-sided and dual-sided horizontal bar spectrum.
- Integer band-rotation scrolling.
- Two-color vertical gradient and band gradient.
- Band-gradient color rotation linked to integer scrolling.
- Still preview and actual-audio motion preview.
- 30-second preview render and full render.
- Optional Compare/Darken matte pair output.
- Pair-safe no-overwrite filename handling.
- Japanese / English UI.
- Tooltips for current controls.

## UI cleanup

Background color has been moved to the Advanced tab. It is no longer treated as a common visual setting because normal operation uses a black main background and pair-output matte generation uses a white matte background automatically.

## Pair output behavior

Pair output does not alter the main video. The matte video is rendered after the main video from the same transformed `bar_values`, using white background and black bars. This preserves frame alignment between main and matte.

## Recommended next branch

The next development branch should start from v1.1.1. LED/segmented digital bars are a suitable next feature, but should remain outside v1.1.1 because they change bar drawing semantics and require separate visual validation.
