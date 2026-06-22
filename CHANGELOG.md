# Changelog

## v1.1.2 (setup fix)

- Updated `setup.bat` display version.
- Switched setup to the Python Launcher's `py -3` command.
- Added a Python 3.10+ check before creating `.venv`.
- Documented the Python 3.10+ and `py -3` setup requirement in README and USER_GUIDE.

## v1.1.1

Stable release for GitHub publication.

- Added Compare/Darken matte pair output.
- Main output is always the normal spectrum video.
- Optional matte output uses white background and black spectrum shape.
- Pair output shares the same analyzed/transformed bar values, so main and matte stay frame-aligned.
- Improved pair filename collision handling: if either main or matte filename exists, both advance to the same numeric suffix.
- Moved background color to the Advanced tab because normal overlay workflows should use black background; matte output uses white automatically.
- Added and reviewed tooltips for newly added and previously uncovered UI controls.
- Added two-color vertical gradient and band gradient.
- Band gradient rotates together with integer band scrolling.
- Added single-sided / dual-sided bar display.
- Added integer band-rotation scrolling.
- Added preview-fit controls and scrollable settings panes.
- Updated README, USER_GUIDE, DEVELOPMENT_NOTES, and TEST_REPORT for stable release.

## v1.0.0

Initial public release.

- Local Python/Tkinter GUI for generating silent MP4 spectrum-analyzer overlay videos from audio files.
- Dynamic spectrum motion processing.
- Visual preview and actual-audio motion preview.
- 30-second preview render and full render.
- System/user presets.
- Japanese / English UI.
- Windows setup and launch batch files.
- MIT License.
