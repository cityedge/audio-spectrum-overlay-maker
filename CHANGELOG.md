# Changelog

## v1.5.0

- SSVC連携JSONに、生成済み素材の不透明度と半透明時の推奨合成方式を追加。正常生成した動画・マット・元音源を一組で保持し、生成後の設定変更やキャンセルによる情報の混在を防止。
- 同梱SSVCをv1.1.1へ更新。半透明素材の自動判定・乗算＋加算・マット必須化に対応。単体プロジェクト用のREADME_SSVC.mdは配布対象外。
- 不透明度0～100%を追加（初期値100%）。100%は従来出力を保持し、100%未満はフロントとマットを対応補正。GUIは市松背景で透け具合を表示。
- 半透明出力時は黒背景・グローなしに統一し、乗算＋加算およびDifferenceによる加算代用向けに出力。
- 「白PNGも出力」を追加（初期値OFF）。動画の正常生成後に、実際の出力解像度と同サイズの完全白RGB画像を保存。既存PNGは上書きしない。

- 全画面キャンバス出力を追加。初期値OFF、1920×1080、中央下、横・縦オフセット0。9方向の配置と正負のpxオフセットに対応。
- メイン／マット、プレビューMP4、全体生成、GUIの見た目・動きプレビューに配置を反映。Post Transform後に配置し、描画領域のサイズと既存の変形動作を維持。
- 日英の設定・ツールチップ、ユーザープリセット保存、出力サイズの入力検証に対応。

## v1.4.1

- デジタル描画を専用経路で高速化。小片の形状・色・角丸の描画結果を再利用し、多数のバー・分割数でも処理負荷を大幅に低減。
- プレビュー、メイン動画、マット動画に自動適用。ピーク表示各モード、グラデーション、スクロール、グロー、Post Transformとの組み合わせを維持。
- 従来経路との画素比較と、メイン／マットMP4をデコードした全フレームの一致を確認。
- 高域ブーストの量とカーブを見た目プレビューにも反映。
- Composer連携のインターフェイスと既存プリセット形式は変更なし。

## v1.4.0

- Expanded the visible-bar choices through 128: 80, 96, 112, and 128 are now available in addition to the existing values. Advanced Custom internal-analysis choices now mirror the visible-bar choices.
- Added a cancel button for active preview-video and full-video rendering. The default removes partial main/matte outputs.
- Added an advanced `Keep Partial Videos on Cancel` option. Kept main/matte videos are independently finalized and may have different durations.

## v1.3.2

- Replaced Peak Hold ON/OFF with a display mode dropdown: Off, Peak Markers, Peaks Only, and Peaks as Bars.
- Added trial high-frequency boost controls: `High boost dB` and `High boost curve`.
- Expanded high-frequency boost range to 36 dB.
- Added the `Moderately Steep` high-frequency boost curve between `Standard` and `Steep`.
- High-frequency boost is display-only and does not affect audio-reactive scaling input.

## v1.3.1

- Added black-background-only Edge Glow for main output.
- Simplified Edge Glow to one dropdown: `None`, `Light`, `Standard`, and `Strong`.
- All Edge Glow strengths use a one-pixel four-direction spread.
- Legacy v1.3.1 presets with Edge Glow enabled are read as `Standard`; the old glow strength value is ignored.
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
