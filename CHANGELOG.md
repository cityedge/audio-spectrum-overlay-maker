# Changelog

## v1.0.0

Official first release of Audio Spectrum Overlay Maker.

- Provides a local Python/Tkinter GUI for generating silent MP4 spectrum-analyzer overlay videos from audio files.
- Supports visible bar counts: 18 / 24 / 32 / 48 / 64.
- Uses separated analysis and transformation layers so perceived motion remains stable across bar counts.
- Includes Dynamic motion processing with relative peak normalization, pulse emphasis, attack/release smoothing, and absolute silence gating.
- Supports automatic or manual frequency range settings.
- Includes system presets:
  - 01 Dynamic Standard
  - 02 Dynamic Active
  - 03 Dynamic Smooth
- Supports user preset save/delete.
- Supports qualitative motion controls and detailed advanced parameters.
- Includes visual preview, actual-audio motion preview, stop button, 30-second preview MP4 generation, and full render.
- Prevents overwriting output files by automatically appending ` (1)`, ` (2)`, etc.
- Adds Japanese / English UI switching.
- Includes full `USER_GUIDE.md`.
- Includes Windows helper batch files: `setup.bat` and `start.bat`.
