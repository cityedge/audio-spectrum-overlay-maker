# v1.1.1 Test Report

## Automated checks

- Python compile check: passed for all Python files
- spectrum_engine import: passed
- VERSION: 1.1.1
- runtime_app_dir() source-mode check: passed
- app-side bin lookup check: passed
- resolve_external_tool("ffmpeg") prefers local bin folder: passed
- PATH fallback after local bin removal: passed

## ffmpeg / ffprobe lookup order

1. App-side `bin` folder
2. PATH fallback
