# v1.2.0 Test Report

## Automated checks

- Python compile check: passed for all Python files, including bundled `final_composer.py`
- spectrum_engine import: passed
- VERSION: 1.2.0
- Composer handoff JSON blank-value behavior: passed
- Bundled file check: `final_composer.py` and `USER_MANUAL_SSVC.md` included
- Package zip check: no `__pycache__` entries

## ffmpeg / ffprobe lookup order

1. App-side `bin` folder
2. PATH fallback
