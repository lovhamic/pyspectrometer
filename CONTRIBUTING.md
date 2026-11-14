# Contributing to PySpectrometer (Image Folder Edition)

Thank you for your interest in contributing to PySpectrometer. We welcome contributions, bug reports, feature suggestions, and documentation improvements.

## Code of Conduct

All contributors and participants are expected to adhere to respectful, professional standards in all communications and technical reviews.

## How to Contribute

### Reporting Bugs

1. Check existing GitHub Issues to see if the bug has already been reported.
2. If not, open a new Issue using the Bug Report template.
3. Include detailed steps to reproduce the issue, OS environment, Python version, and any relevant error logs or sample images.

### Suggesting Enhancements

1. Open a new Issue using the Feature Request template.
2. Clearly explain the proposed functionality, motivation, and potential optical/scientific considerations.

### Submitting Code Changes

1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/PySpectrometer.git
   cd PySpectrometer
   ```
3. Create a descriptive feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. Set up your development environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
5. Make your modifications, adhering to PEP 8 standards.
6. Run the test suite to ensure all tests pass:
   ```bash
   python -m unittest discover -s tests
   ```
7. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "Add feature description"
   ```
8. Push your branch to GitHub:
   ```bash
   git push origin feature/your-feature-name
   ```
9. Submit a Pull Request targeting the `main` branch.

## Development Guidelines

- Keep pull requests focused on a single change or fix.
- Ensure all optical calculations and calibration transformations maintain numerical accuracy.
- Maintain broad compatibility across Windows, Linux, and macOS.
- Ensure any user-facing messages or documentation maintain a professional tone without emojis.
