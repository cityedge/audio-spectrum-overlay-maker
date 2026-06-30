# Audio Spectrum Overlay Maker v1.3.1 Development Notes

## Architecture

The application is split into focused modules:

```text
app.py                  GUI
spectrum_types.py       dataclasses and version
spectrum_audio.py       ffmpeg/ffprobe audio decode
spectrum_analysis.py    FFT and SpectrumData creation
spectrum_motion.py      dynamic motion shaping
spectrum_transform.py   display-bar aggregation and integer scrolling
spectrum_peak.py        peak-hold values
spectrum_parts.py       bar-spectrum visual part
spectrum_primitives.py  primitive rendering
spectrum_draw.py        drawing facade
spectrum_post_transform.py post-render frame coordinate mapping
spectrum_encoder.py     ffmpeg rawvideo encoder
spectrum_workflow.py    preview/full render workflows
spectrum_engine.py      compatibility facade
spectrum_utils.py       shared utilities and tool lookup
```

`app.py` should call the render pipeline through `spectrum_engine.py` / `spectrum_workflow.py` rather than duplicating analysis or encoding logic.

## Processing Order

```text
audio decode
-> FFT analysis
-> dynamic motion shaping
-> display-bar transform / scrolling
-> peak-hold value generation
-> frame drawing
-> optional edge glow
-> Post Transform
-> ffmpeg encoding
```

Post Transform is intentionally after drawing. The drawing layer should not gain special branches for rotation, trapezoid, or audio-reactive scale.

Edge Glow is intentionally before Post Transform. It is part of the rendered main spectrum appearance, so rotation and trapezoid transforms carry the glow with the spectrum.

## Pair Output Design

Pair output is implemented at the workflow layer after one audio-analysis pass:

```text
SpectrumData
-> transform_spectrum_data()
-> bar_values
-> peak_values
-> render main video
-> render matte video from the same values
```

The matte video uses:

```text
background_color = white
bar_color        = black
bar_color2       = black
color_mode       = vertical
```

The main video keeps the user's normal `RenderStyle`. Pair-output ON/OFF does not change the main output.

When pair output is enabled, main and matte `render_video()` calls are submitted to a two-worker `ThreadPoolExecutor`. Both receive the same values and transform settings.

## Post Transform Design

`PostTransformSettings` is the public settings object. `resolve_post_transform()` converts it into a resolved per-frame transform. `PostTransformApplier` caches static source maps and recomputes maps when audio-reactive scale changes.

Current transforms:

- identity / none
- rotation
- vertical trapezoid
- horizontal trapezoid
- combined trapezoid + rotation
- static scale plumbing
- audio-reactive scale

The source canvas size is preserved. Sampling uses inverse mapping from output pixels to source pixels. Fill color is provided by the caller, so main output fills black and matte output fills white.

## Audio-Reactive Scale

Audio-reactive scale is disabled unless `audio_scale_enabled` is true. This prevents a non-100 target value from accidentally activating scaling.

The envelope is:

```text
raw display bar values
-> optional low-band subset
-> mean energy
-> threshold/ceiling normalization
-> peak-hold style hold/decay
-> scale interpolation
```

The scale formula supports enlargement and shrink:

```text
scale = 100 + (target_scale - 100) * energy
```

## Presets

System presets are defined in `preset_manager.py`. v1.3.1 ships 12 system presets. User presets live in `presets_user.json`, which is ignored by Git and is not part of the release zip.

## ffmpeg / ffprobe Lookup

Tool lookup is centralized in `spectrum_utils.find_external_tool()` and `spectrum_utils.resolve_external_tool()`. The lookup order is:

1. app-side `bin`
2. PATH

When PyInstaller freezes the app, `runtime_app_dir()` resolves to the executable directory.
