# Audio Spectrum Overlay Maker v1.1.1 Development Notes

## Architecture

The application is split into focused modules:

```text
app.py                 GUI
spectrum_types.py      dataclasses and version
spectrum_audio.py      ffmpeg/ffprobe audio decode
spectrum_analysis.py   FFT and SpectrumData creation
spectrum_motion.py     Dynamic motion shaping
spectrum_transform.py  display-bar aggregation and scroll transform
spectrum_parts.py      bar-spectrum visual part
spectrum_primitives.py primitive rendering
spectrum_draw.py       drawing facade
spectrum_encoder.py    ffmpeg rawvideo encoder
spectrum_workflow.py   preview/full render workflows
```

`app.py` should call the engine through `spectrum_engine.py` / `spectrum_workflow.py` rather than duplicating analysis or encoder logic.

## Pair output design

Pair output is implemented at the workflow layer after one audio-analysis pass:

```text
audio decode
↓
SpectrumData
↓
transform_spectrum_data()
↓
bar_values
↓
render main video
↓
render matte video from the same bar_values
```

The matte video uses:

```text
background_color = white
bar_color        = black
bar_color2       = black
color_mode       = vertical
```

The main video keeps the user's normal `RenderStyle`. Pair-output ON/OFF does not change the main output.

## Pair filename handling

Pair output uses `unique_output_pair()` in `spectrum_workflow.py`. If either the main or matte output path exists, both filenames advance to the same numeric suffix.

## UI policy

The Visual tab should contain common visual controls. Advanced or special-use controls should go to the Advanced tab. Background color is advanced because standard operation uses black background and pair-output matte uses white automatically.

## Future feature branch

The next feature branch can start from v1.1.1. Candidate features:

- LED / segmented digital bars.
- Peak hold.
- Alternative visuals: vertical bars, dots, area graph, circular bars.

LED/segmented bars should be developed after this stable release because they change the bar drawing semantics more deeply than color or pair output.


### v1.1.1 note

ffmpeg / ffprobe lookup is centralized in `spectrum_utils.find_external_tool()` and `spectrum_utils.resolve_external_tool()`. The lookup order is app-side `bin` first, then PATH. When PyInstaller freezes the app, `runtime_app_dir()` resolves to the directory containing the executable.
