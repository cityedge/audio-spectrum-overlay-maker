# Audio Spectrum Overlay Maker v1.4.1 Release Notes

v1.4.1 はデジタル描画を大幅に高速化する更新です。小片の形状・色・角丸を再利用することで、多数のバー・分割数を使う設定の描画負荷を軽減しました。設定変更は不要で、プレビューとメイン／マット出力に自動適用されます。

720×280・96バー・64分割、30fpsの2秒動画で、メイン／マット同時MP4出力は **19.70秒から2.41秒** になりました。両側デジタル、ピーク片、色スクロール、回転、縦横台形、音量連動拡大、メインの標準グローを併用した測定です。音声解析は含みません。結果はPC性能・解像度・設定によって変わります。

従来描画との画素比較を行い、生成MP4をデコードした結果も、メイン／マットそれぞれ全60フレームが完全一致しました。詳細は `TEST_REPORT.md` を参照してください。

## Highlights

- Accelerated digital/LED rendering with cached segment shapes and colors, preserving peak modes, gradients, scrolling, glow, and Post Transform combinations.
- High-frequency boost amount and curve now affect the still preview.
- Existing preset format and Composer handoff interface are unchanged.

## Retained v1.4.0 Features

- Peak Hold is a display mode dropdown: Off, Peak Markers, Peaks Only, or Peaks as Bars.
- Visible bar counts now reach 128, with 80, 96, and 112 available between 64 and 128.
- Advanced Custom internal-analysis choices now mirror visible bar choices, so 80/96/112/128 can use one analysis band per visible bar.
- Preview-video and full-video rendering can be cancelled from the main action area.
- Default cancellation removes incomplete main and matte MP4 files.
- Advanced `Keep Partial Videos on Cancel` finalizes and retains playable partial MP4s for visual inspection.

## Partial Video Compatibility

When partial-video retention is enabled with pair output, main and matte encoders stop independently. Their durations can differ, so retained files are not a compositing-ready main/matte pair. Full renders that complete normally retain the usual frame-alignment guarantee.

## Existing v1.3.x Features

v1.4.1 continues to include the Post Transform layer, rotation, vertical/horizontal trapezoid transforms, audio-reactive scaling, edge glow, high-frequency boost, scrolling, digital bars, parallel main/matte output, and SRT Spectrum Video Composer handoff.

## Packaging Notes

- Source archive: `audio_spectrum_overlay_maker_v1_4_1.zip`.

- `ffmpeg.exe` and `ffprobe.exe` are not included in the source release zip; only `bin\README.txt` is included.
- `final_composer.py` and `USER_MANUAL_SSVC.md` are included without changing the handoff interface.
- PyInstaller EXE builds are produced separately from the source release package.
