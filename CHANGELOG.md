# Changelog

## v1.3.1

- Added black-background-only Edge Glow for main output.
- Edge Glow spreads rendered spectrum colors by one pixel in eight directions before Post Transform, then restores the original frame on top.
- Matte output remains unchanged, and Edge Glow is automatically disabled when the detailed background color is not black.
- Refreshed bundled `final_composer.py` and `USER_MANUAL_SSVC.md` without changing the handoff interface.

## v1.3.0

Stable release for the Post Transform and SRT Composer generation.

- Added peak-hold rendering as a separate marker layer above the normal bar body.
- Peak markers hold each bar's recent maximum for a configurable time, then decay downward until the current bar catches up.
- Added peak-hold controls: enable/disable, hold milliseconds, decay milliseconds, normal-bar marker size percent, and digital marker segment count.
- Changed the default peak-hold timing to 100ms hold / 300ms decay.
- Peak markers work with single-sided bars, dual-sided bars, scrolling, vertical/band/loop-band gradients, digital segmented bars, GUI motion preview, main output, and matte output.
- Peak markers now scroll together with their source bands when integer scrolling is enabled.
- Added an explicit Post Transform layer after frame drawing and before encoding.
- Post Transform supports static rotation, vertical trapezoid, horizontal trapezoid, combined trapezoid + rotation, and audio-reactive scaling.
- Main and matte outputs use the same Post Transform, preserving canvas size; exposed areas are filled with the frame background color.
- Added Visual-tab controls for rotation, vertical trapezoid, horizontal trapezoid, and audio-reactive scaling.
- Added reset buttons for rotation and trapezoid controls.
- Added audio-reactive scaling with explicit enable/disable checkbox, 80-150% target scale, hold/decay envelope, start threshold, ceiling, and low-band-only detection.
- Added low-band reference range setting in the Advanced tab.
- Added 2-second and 10-second in-app motion preview buttons.
- Added automatic frequency range display next to the Auto/Manual frequency selector.
- Render main and matte pair outputs in parallel when pair output is enabled.
- Replaced `10 Minimal Lower Bar` with `10 Trapezoid Neon`, `11 Vertical Scroll`, and `12 Pulsating LED Scroll`.
- Enabled peak hold for the more energetic and digital system presets while keeping basic and subtle presets quieter.
- Fixed SRT Spectrum Video Composer lookup for PyInstaller builds by searching the PyInstaller extraction directory before falling back to the EXE/app directory.

## v1.3-alpha1

Internal alpha package before the v1.3.0 stabilization pass.

## v1.2.0

- Added optional digital/LED-style segmented bar rendering.
- Digital bars use on/off vertical segments only, with configurable segment count and pixel gap.
- Digital rendering works through the existing drawing layer, so single-sided/dual-sided display, scrolling, gradients, preview, main output, and matte output share the same analyzed bar values.
- Replaced the early motion-oriented system presets with 10 visual showcase presets covering basic white overlays, dual bars, gradients, scrolling, digital/LED styles, and subtle lower-third use.
- Digital showcase presets use 32 visible bars with 16 digital segments per bar.
- Added loop band gradient mode, where both horizontal edges use color 1 and the center uses color 2 for smoother wrapped scrolling.
- Updated the scrolling showcase presets to use loop band gradient.
- Added an optional external handoff button for SRT Spectrum Video Composer. The app writes a UUID handoff JSON with only audio, spectrum video, and matte video paths, then starts itself in composer-launch mode so `final_composer.py` is imported only in the child process.
- Composer handoff can now be opened even before audio or spectrum files are available; missing handoff values are passed as blank strings.
- Changed the matte-pair output option to default ON.
- Swapped the lower action button positions so `Open Output Folder` sits near render controls and the composer button sits on the right.
- Included `final_composer.py` and `USER_MANUAL_SSVC.md` in the package so SRT Spectrum Video Composer is available out of the box.

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
