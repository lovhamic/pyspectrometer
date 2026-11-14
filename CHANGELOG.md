# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0] - 2026-11-15

### Added
- Standard Python packaging (`pyproject.toml`) and console script entry point `pyspectrometer`.
- Comprehensive automated test suite (`tests/test_spectrometer.py`) covering calibration parsing, optical calculations, image loading, peak-hold mechanics, and format validation.
- Continuous Integration workflow via GitHub Actions supporting Linux, macOS, and Windows on Python 3.9 through 3.13.
- In-depth calibration reference documentation (`docs/CALIBRATION_GUIDE.md`) detailing standard emission lines for calibration (mercury-vapor, helium-neon, diode lasers, and solar Fraunhofer lines).
- Sample spectrum data and test assets (`samples/sample_spectrum.png` and `samples/sample_spectrum.csv`).
- Absolute path notifications when saving snapshots and CSV files.
- `main()` invocation interface for programmatic and CLI execution.

### Changed
- Standardized directory layout for open-source GitHub publishing.
- Improved error handling in GUI calibration input validation.
- Updated documentation and contributor guides to professional standards.

## [3.1.0] - 2021-05-20

### Added
- Static spectrum image loading from disk folders or individual files.
- Image folder navigation controls (Previous / Next).
- Natural alphanumeric sorting of image files.
- Flexible calibration argument syntax for command-line execution.
- EXIF orientation correction for mobile and camera-captured images.

### Changed
- Decoupled video capture loop into static image processing backend.

## [1.0.0] - 2021-05-01

### Added
- Initial release of PySpectrometer by Les Wright.
- Real-time video frame acquisition and spectral profile extraction.
- 2-point pixel-to-wavelength linear calibration.
- Savitzky-Golay filtering and peak detection via PeakUtils.
- Peak Hold feature for capturing transient emission peaks.
- Snapshot export for high-resolution graph images and CSV data.
