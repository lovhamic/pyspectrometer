# Wavelength Calibration Guide for PySpectrometer

This guide outlines the mathematical foundations, standard calibration sources, and step-by-step procedures for calibrating PySpectrometer using static spectrum images.

## 1. Principles of Diffraction and Calibration

### The Grating Equation

PySpectrometer is designed to process optical spectra dispersed by a transmission diffraction grating (typically 500 to 1200 lines/mm, or derived from blank DVD/CD media).

The dispersion across the sensor is governed by the grating equation:

```text
d * (sin(alpha) + sin(beta)) = m * lambda
```

Where:
- `d` is the grating slit spacing (groove period).
- `alpha` is the angle of incidence.
- `beta` is the angle of diffraction.
- `m` is the diffraction order (typically `m = 1`).
- `lambda` is the optical wavelength in nanometers.

### Linear Pixel-to-Wavelength Approximation

For small diffraction angles across a planar CMOS image sensor:

```text
sin(beta) ≈ tan(beta) = x / L
```

Where `x` is the horizontal position along the sensor plane and `L` is the distance between the grating and sensor. Over the visible spectrum (380 nm to 750 nm), the dispersion is approximately linear:

```text
lambda(x) = lambda_0 + (d_lambda / dx) * x
```

PySpectrometer utilizes a two-point linear calibration model determined by two known reference points:

```text
Point 1: (pixel_1, wavelength_1)
Point 2: (pixel_2, wavelength_2)
```

The calibration slope (nm per pixel) and intercept are computed as:

```text
nm_per_pixel = |wavelength_2 - wavelength_1| / |pixel_2 - pixel_1|
zero_wavelength = wavelength_1 - (pixel_1 * nm_per_pixel)
```

## 2. Standard Reference Calibration Sources

To establish accurate wavelength calibration, select light sources with well-documented, narrow spectral emission lines.

### Compact Fluorescent Lamps (CFL / Fluorescent Tube)

Compact fluorescent lamps contain low-pressure mercury vapor combined with rare-earth phosphors. They provide prominent, readily accessible emission lines across the entire visible spectrum:

| Element / Phosphor | Nominal Wavelength (nm) | Observed Color | Relative Intensity |
| :--- | :--- | :--- | :--- |
| Mercury (Hg) | 404.7 | Deep Violet | Strong |
| Mercury (Hg) | 435.8 | Blue | Very Strong |
| Terbium (Tb3+) | 487.0 | Cyan-Blue | Medium |
| Terbium (Tb3+) | 542.4 | Bright Green | Extremely Strong |
| Mercury (Hg) | 546.1 | Green | Strong |
| Mercury (Hg) | 577.0 / 579.1 | Yellow Doublet | Medium |
| Europium (Eu3+) | 611.2 | Orange-Red | Extremely Strong |

Recommended CFL calibration pair:
- **Reference Point 1**: 404.7 nm (Hg violet line) or 435.8 nm (Hg blue line)
- **Reference Point 2**: 546.1 nm (Hg green line) or 611.2 nm (Eu red peak)

### Diode and Gas Lasers

Commercial laser pointers provide monochromatic emission lines ideal for pinpoint calibration:

| Laser Type | Wavelength (nm) | Color |
| :--- | :--- | :--- |
| Violet Diode | 405.0 | Violet |
| Argon Ion | 488.0 | Cyan |
| Green DPSS (Nd:YAG frequency-doubled) | 532.0 | Green |
| Helium-Neon (He-Ne) | 632.8 | Red |
| Red Diode | 650.0 (measure exact spec) | Red |

Recommended Laser calibration pair:
- **Reference Point 1**: 405.0 nm (Violet laser)
- **Reference Point 2**: 532.0 nm (Green DPSS laser)

## 3. Interactive GUI Calibration Workflow

1. **Launch PySpectrometer with a Calibration Target**:
   ```bash
   python pyspectrometer_image_folder.py --folder samples/sample_spectrum.png
   ```

2. **Verify Slit Alignment**:
   Ensure the spectrum is oriented horizontally and intersects the central white alignment guideline displayed in the preview canvas.

3. **Reset Existing Points**:
   Click the **Clear** button. The Wavelength 1 and Wavelength 2 labels will display `Click graph to add point!`.

4. **Select Reference Point 1**:
   - Locate the first known spectral peak on the graph (e.g., the 405 nm peak).
   - Click directly on the center of the peak on the intensity graph.
   - The horizontal pixel position will register in the `Wavelength 1` marker.
   - Type the known wavelength value into the `Wavelength 1` entry box (e.g., `405`).

5. **Select Reference Point 2**:
   - Locate the second known spectral peak on the graph (e.g., the 532 nm peak).
   - Click directly on the center of the peak on the intensity graph.
   - The horizontal pixel position will register in the `Wavelength 2` marker.
   - Type the known wavelength value into the `Wavelength 2` entry box (e.g., `532`).

6. **Lock Calibration**:
   - Click the **Calibrate** button.
   - The button state will switch to `Calibrated` in yellow, and the graph axis ticks will immediately recalculate and display physical nanometer markings.

7. **Verify Calibration**:
   - Inspect intermediate emission lines (such as the 546 nm green line or 611 nm red phosphor line) to verify that detected peaks match theoretical values within +/- 1 to 2 nm.

## 4. Headless and Command-Line Calibration

Once a physical spectrometer apparatus has been calibrated, you can pass the calibration coordinates directly from the terminal without manual clicking:

```bash
python pyspectrometer_image_folder.py --folder /path/to/spectra -c 72:405,304:532
```

Argument format:
```text
-c <pixel1>:<wavelength1>,<pixel2>:<wavelength2>
```

Example with decimal precision:
```bash
python pyspectrometer_image_folder.py -f sample.png -c 72:404.7,304:532.0
```

## 5. Practical Guidelines for Accurate Spectral Capture

- **Slit Width**: A narrow slit (0.1 mm to 0.2 mm) produces sharper emission peaks and higher resolving power at the expense of light throughput.
- **Sensor Saturation**: Avoid overexposing the sensor. Overexposed spectral lines flatten at intensity 255, broadening peak widths and degrading center-of-mass wavelength detection.
- **Grating Alignment**: Mount the diffraction grating perpendicular to the optical axis with grating lines strictly vertical to minimize tilt distortion across the sensor array.
