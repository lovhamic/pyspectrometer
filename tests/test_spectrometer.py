"""
Unit and integration tests for PySpectrometer (Image Folder Edition).
"""

import os
import unittest
import numpy as np
import cv2
import argparse

import pyspectrometer_image_folder as ps


class TestCalibrationParsing(unittest.TestCase):
    """Tests for CLI calibration argument parsing."""

    def setUp(self):
        self.parser = ps.arg_parser()

    def test_standard_colon_comma_format(self):
        args = self.parser.parse_args(["-c", "72:400,304:530"])
        self.assertEqual(args.calibration, ((72, 400), (304, 530)))

    def test_semicolon_separator(self):
        args = self.parser.parse_args(["-c", "72:405; 304:532"])
        self.assertEqual(args.calibration, ((72, 405), (304, 532)))

    def test_float_wavelengths(self):
        args = self.parser.parse_args(["-c", "72:404.7, 304:532.0"])
        self.assertEqual(args.calibration, ((72, 404.7), (304, 532)))

    def test_invalid_calibration_syntax(self):
        import io
        from contextlib import redirect_stderr
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.parser.parse_args(["-c", "invalid_calibration_string"])

    def test_insufficient_points(self):
        import io
        from contextlib import redirect_stderr
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.parser.parse_args(["-c", "72:400"])


class TestWavelengthColorMapping(unittest.TestCase):
    """Tests for physical wavelength to RGB color conversion."""

    def setUp(self):
        self.spec = ps.ImageSpectrometer(ps.App.DEFAULT_CALIBRATION)

    def test_ultraviolet_cutoff(self):
        rgb = self.spec.wavelength_to_rgb(350)
        self.assertEqual(rgb, (0, 0, 0))

    def test_infrared_cutoff(self):
        rgb = self.spec.wavelength_to_rgb(800)
        self.assertEqual(rgb, (0, 0, 0))

    def test_green_laser_line(self):
        r, g, b = self.spec.wavelength_to_rgb(532)
        self.assertGreater(g, r)
        self.assertGreater(g, b)

    def test_red_laser_line(self):
        r, g, b = self.spec.wavelength_to_rgb(650)
        self.assertGreater(r, g)
        self.assertGreater(r, b)

    def test_blue_violet_line(self):
        r, g, b = self.spec.wavelength_to_rgb(420)
        self.assertGreater(b, g)


class TestImageSpectrometerCore(unittest.TestCase):
    """Tests for core spectrometer image processing and data extraction."""

    def setUp(self):
        self.spec = ps.ImageSpectrometer(ps.App.DEFAULT_CALIBRATION)
        self.sample_path = os.path.join(os.path.dirname(__file__), "..", "samples", "sample_spectrum.png")
        self.sample_path = os.path.abspath(self.sample_path)

    def test_empty_state(self):
        self.assertIsNone(self.spec.current_filename())
        self.assertEqual(self.spec.image_count(), 0)
        ret, frame = self.spec.get_frame()
        self.assertFalse(ret)
        self.assertIsNone(frame)
        ret_graph, gdata = self.spec.get_graph()
        self.assertFalse(ret_graph)
        self.assertIsNone(gdata)

    def test_load_nonexistent_target(self):
        ok = self.spec.load_folder("non_existent_folder_or_file_12345")
        self.assertFalse(ok)

    def test_load_sample_file(self):
        if not os.path.exists(self.sample_path):
            self.skipTest("Sample spectrum image not found")

        ok = self.spec.load_folder(self.sample_path)
        self.assertTrue(ok)
        self.assertEqual(self.spec.image_count(), 1)
        self.assertEqual(self.spec.current_index(), 0)
        self.assertEqual(self.spec.current_filename(), "sample_spectrum.png")

    def test_preview_frame_generation(self):
        if not os.path.exists(self.sample_path):
            self.skipTest("Sample spectrum image not found")

        self.spec.load_folder(self.sample_path)
        ret, frame = self.spec.get_frame()
        self.assertTrue(ret)
        self.assertIsNotNone(frame)
        self.assertEqual(frame.shape, (240, 320, 3))

    def test_graph_and_spectral_data(self):
        if not os.path.exists(self.sample_path):
            self.skipTest("Sample spectrum image not found")

        self.spec.load_folder(self.sample_path)
        ret, gdata = self.spec.get_graph()
        self.assertTrue(ret)
        self.assertIsNotNone(gdata)

        graph_image, wavelengths, intensities = gdata
        self.assertEqual(graph_image.shape, (255, 636, 3))
        self.assertEqual(len(wavelengths), 636)
        self.assertEqual(len(intensities), 636)

        # Ensure intensity range is normalized within 0 to 255
        self.assertTrue(all(0 <= val <= 255 for val in intensities))

        # Wavelengths should be monotonically increasing across the spectrum
        self.assertTrue(wavelengths[-1] > wavelengths[0])

    def test_peak_hold_accumulation(self):
        # Create two synthetic 100x640 images with distinct spectral lines
        img1 = np.zeros((100, 640, 3), dtype=np.uint8)
        img1[50, 100] = [200, 200, 200]  # Line at x=100

        img2 = np.zeros((100, 640, 3), dtype=np.uint8)
        img2[50, 300] = [240, 240, 240]  # Line at x=300

        self.spec.frame = img1
        self.spec.holdpeaks = True

        ret1, gdata1 = self.spec.get_graph()
        self.assertTrue(ret1)
        intensity_at_100_first = self.spec.intensity[100]

        self.spec.frame = img2
        ret2, gdata2 = self.spec.get_graph()
        self.assertTrue(ret2)

        # Under Peak Hold, peak at 100 should be preserved even though img2 has no line there
        self.assertEqual(self.spec.intensity[100], intensity_at_100_first)

    def test_recalibration(self):
        if not os.path.exists(self.sample_path):
            self.skipTest("Sample spectrum image not found")

        self.spec.load_folder(self.sample_path)
        new_calibration = ((50, 380), (350, 600))
        self.spec.recalibrate(new_calibration)
        ret, gdata = self.spec.get_graph()
        self.assertTrue(ret)
        wavelengths = gdata[1]
        self.assertEqual(self.spec.calibration, new_calibration)
        self.assertAlmostEqual(wavelengths[50], 380, delta=1.5)


if __name__ == "__main__":
    unittest.main()
