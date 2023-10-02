#!/usr/bin/env python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for consolidate.py."""

import collections
import difflib
import json
import os
import pathlib
import tempfile
import unittest

import consolidate


class TestParseArgs(unittest.TestCase):
    """Test case for parse_args()."""

    def setUp(self):
        """Change the current working directory.

        This will ensure that even if the script is run from elsewhere,
        input_dir arg still defaults to fw-testing-configs.
        """
        self.original_cwd = os.getcwd()
        os.chdir("/tmp")

    def tearDown(self):
        """Restore the original working directory."""
        os.chdir(self.original_cwd)

    def test_command_line_args(self):
        """Test with specified command-line args."""
        input_dir = "foo"
        output_file = "bar"
        argv = ["-i", input_dir, "-o", output_file]
        args = consolidate.parse_args(argv)
        self.assertEqual(args.input_dir, input_dir)
        self.assertEqual(args.output, output_file)

    def test_defaults(self):
        """Test with no command-line args."""
        args = consolidate.parse_args([])
        self.assertEqual(args.output, consolidate.DEFAULT_OUTPUT_FILEPATH)
        # Note: This assertion is not hermetic!
        self.assertTrue("fw-testing-configs" in args.input_dir)
        # Note: This assertion is not hermetic!
        self.assertTrue("DEFAULTS.json" in os.listdir(args.input_dir))


class TestGetPlatformNames(unittest.TestCase):
    """Test case for get_platform_names()."""

    def setUp(self):
        """Create mock fw-testing-configs directory."""
        self.mock_fwtc_dir = (
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )
        mock_platform_names = ["z", "a", "b", "DEFAULTS", "CONSOLIDATED"]
        for platform in mock_platform_names:
            mock_filepath = os.path.join(
                self.mock_fwtc_dir.name, platform + ".json"
            )
            pathlib.Path(mock_filepath).touch()

    def tearDown(self):
        """Destroy mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()

    def test_get_platform_names(self):
        """Verify that platform names load in the correct order.

        The correct order is starting with DEFAULTS, then alphabetical.
        The .json file extension should not be included.
        """
        platforms = consolidate.get_platform_names(self.mock_fwtc_dir.name)
        self.assertEqual(platforms, ["DEFAULTS", "a", "b", "z"])


class TestLoadJSON(unittest.TestCase):
    """Test case for load_json()."""

    def setUp(self):
        """Setup mock fw-testing-configs directory."""
        self.maxDiff = None
        self.mock_fwtc_dir = (
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )
        a_filename = os.path.join(self.mock_fwtc_dir.name, "a.json")
        with open(a_filename, "w", encoding="utf-8") as a_file:
            a_file.write(
                "{\n"
                + '  "platform": "a",\n'
                + '  "ec_capability": {'
                + '    "adc_ectemp": false,\n'
                + '    "arm": false,\n'
                + '    "battery": false,\n'
                + '    "cbi": false,\n'
                + '    "charging": false,\n'
                + '    "doubleboot": false,\n'
                + '    "keyboard": false,\n'
                + '    "lid": false,\n'
                + '    "peci": false,\n'
                + '    "smart_usb_charge": false,\n'
                + '    "thermal": false,\n'
                + '    "usb": true,\n'
                + '    "usbpd_uart": false,\n'  # set as True for test
                + '    "x86": true\n'
                + "  },\n"  # set as True for test
                + '  "cr50_capability": {'
                + '    "ec_hibernate_breaks_rdd": false,\n'
                + '    "wp_on_in_g3": true,\n'
                + '    "rdd_off_in_g3": false,\n'  # set as True for test
                + '    "rdd_leakage": true\n'
                + "  },\n"  # set as True for test
                + '  "minidiag_capability": {'
                + '    "cbmem_preserved_by_ap_reset": true,\n'
                + '    "storage_self_test": false,\n'
                + '    "event_log_launch_count": true\n'
                +
                # set as True for test
                "  }\n"
                + "}"
            )
        defaults_filename = os.path.join(
            self.mock_fwtc_dir.name, "DEFAULTS.json"
        )
        with open(defaults_filename, "w", encoding="utf-8") as defaults_file:
            defaults_file.write(
                "{\n"
                + '  "platform": null,\n'
                + '  "platform.DOC": "foo",\n'
                + '  "ec_capability": {'
                + '    "adc_ectemp": null,\n'
                + '    "arm": null,\n'
                + '    "battery": null,\n'
                + '    "cbi": null,\n'
                + '    "charging": null,\n'
                + '    "doubleboot": null,\n'
                + '    "keyboard": null,\n'
                + '    "lid": null,\n'
                + '    "peci": null,\n'
                + '    "smart_usb_charge": null,\n'
                + '    "thermal": null,\n'
                + '    "usb": null,\n'
                + '    "usbpd_uart": null,\n'
                + '    "x86": null,\n'
                + '    "default_true": true,\n'
                + '    "default_false": false\n'
                + "  },\n"
                + '  "cr50_capability": {'
                + '    "ec_hibernate_breaks_rdd": null,\n'
                + '    "wp_on_in_g3": null,\n'
                + '    "rdd_off_in_g3": null,\n'
                + '    "rdd_leakage": null,\n'
                + '    "default_true": true,\n'
                + '    "default_false": false\n'
                + "  },\n"
                + '  "minidiag_capability": {'
                + '    "cbmem_preserved_by_ap_reset": null,\n'
                + '    "storage_self_test": null,\n'
                + '    "event_log_launch_count": null,\n'
                + '    "default_true": true,\n'
                + '    "default_false": false\n'
                + "  }\n"
                + "}"
            )

    def tearDown(self):
        self.mock_fwtc_dir.cleanup()

    def test_load_json(self):
        """Verify that we correctly load platform JSON contents."""
        expected = collections.OrderedDict()
        expected["DEFAULTS"] = collections.OrderedDict()
        expected["DEFAULTS"]["platform"] = None
        expected["DEFAULTS"]["platform.DOC"] = "foo"
        expected["DEFAULTS"]["ec_capability"] = ["default_true"]
        expected["DEFAULTS"]["cr50_capability"] = ["default_true"]
        expected["DEFAULTS"]["minidiag_capability"] = ["default_true"]
        expected["a"] = collections.OrderedDict()
        expected["a"]["platform"] = "a"
        expected["a"]["ec_capability"] = ["default_true", "usb", "x86"]
        expected["a"]["cr50_capability"] = [
            "default_true",
            "rdd_leakage",
            "wp_on_in_g3",
        ]
        expected["a"]["minidiag_capability"] = [
            "cbmem_preserved_by_ap_reset",
            "default_true",
            "event_log_launch_count",
        ]
        actual = consolidate.load_json(
            self.mock_fwtc_dir.name, ["DEFAULTS", "a"]
        )
        self.assertEqual(actual, expected)


class TestWriteOutput(unittest.TestCase):
    """Test case for write_output()."""

    output_fp = "/tmp/CONSOLIDATED.json"

    def tearDown(self):
        """Clean up output_fp"""
        if os.path.isfile(TestWriteOutput.output_fp):
            os.remove(TestWriteOutput.output_fp)

    def test_write_output(self):
        """Verify that write_output writes JSON and sets to read-only."""
        # Run the function
        mock_json = collections.OrderedDict({"foo": "bar", "bar": "baz"})
        consolidate.write_output(mock_json, TestWriteOutput.output_fp)

        # Verify file contents
        with open(TestWriteOutput.output_fp, encoding="utf-8") as output_file:
            output_contents = output_file.readlines()
        expected = ["{\n", '  "bar": "baz",\n', '  "foo": "bar"\n', "}\n"]
        self.assertEqual(output_contents, expected)

        # Verify that file is read-only
        with self.assertRaises(PermissionError):
            with open(
                TestWriteOutput.output_fp, "w", encoding="utf-8"
            ) as output_file:
                output_file.write("foo")


class TestInvalidECCapability(unittest.TestCase):
    """Test case for invalid ec_capability configurations"""

    output_fp = "/tmp/CONSOLIDATED.json"

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.mock_fwtc_dir = (
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, "a.json")
        with open(a_json_fp, "w", encoding="utf-8") as a_json_file:
            a_json = collections.OrderedDict(
                {
                    "platform": "a",
                    "firmware_screen": 0.5,
                    "ec_capability": {
                        "adc_ectemp": True,
                        "arm": True,
                        "battery": False,
                        "cbi": False,
                        "charging": False,
                        "doubleboot": False,
                        "keyboard": False,
                        "lid": False,
                        "peci": False,
                        "smart_usb_charge": False,
                        "thermal": False,
                        "usb": True,
                        "usbpd_uart": False,
                        "x86": True,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": True,
                        "wp_on_in_g3": True,
                        "rdd_off_in_g3": False,
                        "rdd_leakage": False,
                    },
                }
            )
            json.dump(a_json, a_json_file)
        z_json_fp = os.path.join(self.mock_fwtc_dir.name, "z.json")
        with open(z_json_fp, "w", encoding="utf-8") as z_json_file:
            z_json = collections.OrderedDict(
                {
                    "platform": "z",
                    "parent": "a",
                    "firmware_screen": 10,
                    "ec_capability": {  # override a:
                        "arm": False,
                        "FAKE": True,  # invalid
                    },
                    "cr50_capability": {
                        "wp_on_in_g3": False,
                        "rdd_off_in_g3": True,
                    },
                }
            )
            json.dump(z_json, z_json_file)
        defaults_json_fp = os.path.join(
            self.mock_fwtc_dir.name, "DEFAULTS.json"
        )
        with open(
            defaults_json_fp, "w", encoding="utf-8"
        ) as defaults_json_file:
            defaults_json = collections.OrderedDict(
                {
                    "platform": None,
                    "platform.DOC": "foo",
                    "ec_capability": {
                        "adc_ectemp": None,
                        "arm": None,
                        "battery": None,
                        "cbi": None,
                        "charging": None,
                        "doubleboot": None,
                        "keyboard": None,
                        "lid": None,
                        "peci": None,
                        "smart_usb_charge": None,
                        "thermal": None,
                        "usb": None,
                        "usbpd_uart": None,
                        "x86": None,
                        "default_true": True,
                        "default_false": False,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": None,
                        "wp_on_in_g3": None,
                        "rdd_off_in_g3": None,
                        "rdd_leakage": None,
                        "default_true": True,
                        "default_false": False,
                    },
                }
            )
            json.dump(defaults_json, defaults_json_file)

    def tearDown(self):
        """Delete output file and mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()
        if os.path.isfile(TestMain.output_fp):
            os.remove(TestMain.output_fp)

    def test_main(self):
        with self.assertRaises(consolidate.FormatException):
            # Should raise error since child has invalid capability
            argv = ["-i", self.mock_fwtc_dir.name, "-o", TestMain.output_fp]
            consolidate.main(argv)


class TestMissingECCapability(unittest.TestCase):
    """Test case for missing ec_capability configurations"""

    output_fp = "/tmp/CONSOLIDATED.json"

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.mock_fwtc_dir = (
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, "a.json")
        with open(a_json_fp, "w", encoding="utf-8") as a_json_file:
            a_json = collections.OrderedDict(
                {
                    "platform": "a",
                    "firmware_screen": 0.5,
                    "ec_capability": {
                        "adc_ectemp": True,
                        "arm": True,
                        # Removed battery, cbi keys
                        "charging": False,
                        "doubleboot": False,
                        "keyboard": False,
                        "lid": False,
                        "peci": False,
                        "smart_usb_charge": False,
                        "thermal": False,
                        "usb": True,
                        "usbpd_uart": False,
                        "x86": True,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": True,
                        "wp_on_in_g3": True,
                        "rdd_off_in_g3": False,
                        "rdd_leakage": False,
                    },
                }
            )
            json.dump(a_json, a_json_file)
        z_json_fp = os.path.join(self.mock_fwtc_dir.name, "z.json")
        with open(z_json_fp, "w", encoding="utf-8") as z_json_file:
            z_json = collections.OrderedDict(
                {
                    "platform": "z",
                    "parent": "a",
                    "firmware_screen": 10,
                    "ec_capability": {  # override a:
                        "arm": False,
                        "keyboard": True,
                        "lid": True,
                    },
                    "cr50_capability": {
                        "wp_on_in_g3": False,
                        "rdd_off_in_g3": True,
                    },
                }
            )
            json.dump(z_json, z_json_file)
        defaults_json_fp = os.path.join(
            self.mock_fwtc_dir.name, "DEFAULTS.json"
        )
        with open(
            defaults_json_fp, "w", encoding="utf-8"
        ) as defaults_json_file:
            defaults_json = collections.OrderedDict(
                {
                    "platform": None,
                    "platform.DOC": "foo",
                    "ec_capability": {
                        "adc_ectemp": None,
                        "arm": None,
                        "battery": None,
                        "cbi": None,
                        "charging": None,
                        "doubleboot": None,
                        "keyboard": None,
                        "lid": None,
                        "peci": None,
                        "smart_usb_charge": None,
                        "thermal": None,
                        "usb": None,
                        "usbpd_uart": None,
                        "x86": None,
                        "default_true": True,
                        "default_false": False,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": None,
                        "wp_on_in_g3": None,
                        "rdd_off_in_g3": None,
                        "rdd_leakage": None,
                        "default_true": True,
                        "default_false": False,
                    },
                }
            )
            json.dump(defaults_json, defaults_json_file)

    def tearDown(self):
        """Delete output file and mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()
        if os.path.isfile(TestMain.output_fp):
            os.remove(TestMain.output_fp)

    def test_main(self):
        with self.assertRaises(consolidate.FormatException):
            # Should raise error since neither z nor a have all required keys
            argv = ["-i", self.mock_fwtc_dir.name, "-o", TestMain.output_fp]
            consolidate.main(argv)


class TestInvalidCR50Capability(unittest.TestCase):
    """Test case for invalid cr50_capability configurations"""

    output_fp = "/tmp/CONSOLIDATED.json"

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.mock_fwtc_dir = (
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, "a.json")
        with open(a_json_fp, "w", encoding="utf-8") as a_json_file:
            a_json = collections.OrderedDict(
                {
                    "platform": "a",
                    "firmware_screen": 0.5,
                    "ec_capability": {
                        "adc_ectemp": True,
                        "arm": True,
                        "battery": False,
                        "cbi": False,
                        "charging": False,
                        "doubleboot": False,
                        "keyboard": False,
                        "lid": False,
                        "peci": False,
                        "smart_usb_charge": False,
                        "thermal": False,
                        "usb": True,
                        "usbpd_uart": False,
                        "x86": True,
                    },
                    "cr50_capability": {
                        "FAKE": True,  # invalid cr50_capability
                        "wp_on_in_g3": True,
                        "rdd_off_in_g3": False,
                        "rdd_leakage": False,
                    },
                }
            )
            json.dump(a_json, a_json_file)
        defaults_json_fp = os.path.join(
            self.mock_fwtc_dir.name, "DEFAULTS.json"
        )
        with open(
            defaults_json_fp, "w", encoding="utf-8"
        ) as defaults_json_file:
            defaults_json = collections.OrderedDict(
                {
                    "platform": None,
                    "platform.DOC": "foo",
                    "ec_capability": {
                        "adc_ectemp": None,
                        "arm": None,
                        "battery": None,
                        "cbi": None,
                        "charging": None,
                        "doubleboot": None,
                        "keyboard": None,
                        "lid": None,
                        "peci": None,
                        "smart_usb_charge": None,
                        "thermal": None,
                        "usb": None,
                        "usbpd_uart": None,
                        "x86": None,
                        "default_true": True,
                        "default_false": False,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": None,
                        "wp_on_in_g3": None,
                        "rdd_off_in_g3": None,
                        "rdd_leakage": None,
                        "default_true": True,
                        "default_false": False,
                    },
                }
            )
            json.dump(defaults_json, defaults_json_file)

    def tearDown(self):
        """Delete output file and mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()
        if os.path.isfile(TestMain.output_fp):
            os.remove(TestMain.output_fp)

    def test_main(self):
        with self.assertRaises(consolidate.FormatException):
            # Should raise error since child has invalid capability
            argv = ["-i", self.mock_fwtc_dir.name, "-o", TestMain.output_fp]
            consolidate.main(argv)


class TestMissingCR50Capability(unittest.TestCase):
    """Test case for missing cr_50 configurations"""

    output_fp = "/tmp/CONSOLIDATED.json"

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.mock_fwtc_dir = (
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, "a.json")
        with open(a_json_fp, "w", encoding="utf-8") as a_json_file:
            a_json = collections.OrderedDict(
                {
                    "platform": "a",
                    "firmware_screen": 0.5,
                    "ec_capability": {
                        "adc_ectemp": True,
                        "arm": True,
                        "battery": False,
                        "cbi": False,
                        "charging": False,
                        "doubleboot": False,
                        "keyboard": False,
                        "lid": False,
                        "peci": False,
                        "smart_usb_charge": False,
                        "thermal": False,
                        "usb": True,
                        "usbpd_uart": False,
                        "x86": True,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": True,
                        "rdd_off_in_g3": False,  # 'wp_on_in_g3' removed
                        "rdd_leakage": False,
                    },
                }
            )
            json.dump(a_json, a_json_file)
        defaults_json_fp = os.path.join(
            self.mock_fwtc_dir.name, "DEFAULTS.json"
        )
        with open(
            defaults_json_fp, "w", encoding="utf-8"
        ) as defaults_json_file:
            defaults_json = collections.OrderedDict(
                {
                    "platform": None,
                    "platform.DOC": "foo",
                    "ec_capability": {
                        "adc_ectemp": None,
                        "arm": None,
                        "battery": None,
                        "cbi": None,
                        "charging": None,
                        "doubleboot": None,
                        "keyboard": None,
                        "lid": None,
                        "peci": None,
                        "smart_usb_charge": None,
                        "thermal": None,
                        "usb": None,
                        "usbpd_uart": None,
                        "x86": None,
                        "default_true": True,
                        "default_false": False,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": None,
                        "wp_on_in_g3": None,
                        "rdd_off_in_g3": None,
                        "rdd_leakage": None,
                        "default_true": True,
                        "default_false": False,
                    },
                }
            )
            json.dump(defaults_json, defaults_json_file)

    def tearDown(self):
        """Delete output file and mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()
        if os.path.isfile(TestMain.output_fp):
            os.remove(TestMain.output_fp)

    def test_main(self):
        with self.assertRaises(consolidate.FormatException):
            # Should raise error since neither z nor a have all required keys
            argv = ["-i", self.mock_fwtc_dir.name, "-o", TestMain.output_fp]
            consolidate.main(argv)


class TestInvalidMinidiagCapability(unittest.TestCase):
    """Test case for invalid cr50_capability configurations"""

    output_fp = "/tmp/CONSOLIDATED.json"

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.mock_fwtc_dir = (
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, "a.json")
        with open(a_json_fp, "w", encoding="utf-8") as a_json_file:
            a_json = collections.OrderedDict(
                {
                    "platform": "a",
                    "firmware_screen": 0.5,
                    "ec_capability": {
                        "adc_ectemp": True,
                        "arm": True,
                        "battery": False,
                        "cbi": False,
                        "charging": False,
                        "doubleboot": False,
                        "keyboard": False,
                        "lid": False,
                        "peci": False,
                        "smart_usb_charge": False,
                        "thermal": False,
                        "usb": True,
                        "usbpd_uart": False,
                        "x86": True,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": True,
                        "wp_on_in_g3": True,
                        "rdd_off_in_g3": False,
                        "rdd_leakage": False,
                    },
                    "minidiag_capability": {
                        "FAKE": True,  # invalid minidiag_capability
                        "cbmem_preserved_by_ap_reset": True,
                        "storage_self_test": True,
                        "event_log_launch_count": True,
                    },
                }
            )
            json.dump(a_json, a_json_file)
        defaults_json_fp = os.path.join(
            self.mock_fwtc_dir.name, "DEFAULTS.json"
        )
        with open(
            defaults_json_fp, "w", encoding="utf-8"
        ) as defaults_json_file:
            defaults_json = collections.OrderedDict(
                {
                    "platform": None,
                    "platform.DOC": "foo",
                    "ec_capability": {
                        "adc_ectemp": None,
                        "arm": None,
                        "battery": None,
                        "cbi": None,
                        "charging": None,
                        "doubleboot": None,
                        "keyboard": None,
                        "lid": None,
                        "peci": None,
                        "smart_usb_charge": None,
                        "thermal": None,
                        "usb": None,
                        "usbpd_uart": None,
                        "x86": None,
                        "default_true": True,
                        "default_false": False,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": None,
                        "wp_on_in_g3": None,
                        "rdd_off_in_g3": None,
                        "rdd_leakage": None,
                        "default_true": True,
                        "default_false": False,
                    },
                    "minidiag_capability": {
                        "cbmem_preserved_by_ap_reset": None,
                        "storage_self_test": None,
                        "event_log_launch_count": None,
                    },
                }
            )
            json.dump(defaults_json, defaults_json_file)

    def tearDown(self):
        """Delete output file and mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()
        if os.path.isfile(TestMain.output_fp):
            os.remove(TestMain.output_fp)

    def test_main(self):
        with self.assertRaises(consolidate.FormatException):
            # Should raise error since child has invalid capability
            argv = ["-i", self.mock_fwtc_dir.name, "-o", TestMain.output_fp]
            consolidate.main(argv)


class TestMissingMinidiagCapability(unittest.TestCase):
    """Test case for missing cr_50 configurations"""

    output_fp = "/tmp/CONSOLIDATED.json"

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.mock_fwtc_dir = (
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, "a.json")
        with open(a_json_fp, "w", encoding="utf-8") as a_json_file:
            a_json = collections.OrderedDict(
                {
                    "platform": "a",
                    "firmware_screen": 0.5,
                    "ec_capability": {
                        "adc_ectemp": True,
                        "arm": True,
                        "battery": False,
                        "cbi": False,
                        "charging": False,
                        "doubleboot": False,
                        "keyboard": False,
                        "lid": False,
                        "peci": False,
                        "smart_usb_charge": False,
                        "thermal": False,
                        "usb": True,
                        "usbpd_uart": False,
                        "x86": True,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": True,
                        "wp_on_in_g3": True,
                        "rdd_off_in_g3": False,
                        "rdd_leakage": False,
                    },
                    "minidiag_capability": {
                        "cbmem_preserved_by_ap_reset": False,
                        "storage_self_test": False
                        # 'event_log_launch_count' removed
                    },
                }
            )
            json.dump(a_json, a_json_file)
        defaults_json_fp = os.path.join(
            self.mock_fwtc_dir.name, "DEFAULTS.json"
        )
        with open(
            defaults_json_fp, "w", encoding="utf-8"
        ) as defaults_json_file:
            defaults_json = collections.OrderedDict(
                {
                    "platform": None,
                    "platform.DOC": "foo",
                    "ec_capability": {
                        "adc_ectemp": None,
                        "arm": None,
                        "battery": None,
                        "cbi": None,
                        "charging": None,
                        "doubleboot": None,
                        "keyboard": None,
                        "lid": None,
                        "peci": None,
                        "smart_usb_charge": None,
                        "thermal": None,
                        "usb": None,
                        "usbpd_uart": None,
                        "x86": None,
                        "default_true": True,
                        "default_false": False,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": None,
                        "wp_on_in_g3": None,
                        "rdd_off_in_g3": None,
                        "rdd_leakage": None,
                        "default_true": True,
                        "default_false": False,
                    },
                    "minidiag_capability": {
                        "cbmem_preserved_by_ap_reset": None,
                        "storage_self_test": None,
                        "event_log_launch_count": None,
                    },
                }
            )
            json.dump(defaults_json, defaults_json_file)

    def tearDown(self):
        """Delete output file and mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()
        if os.path.isfile(TestMain.output_fp):
            os.remove(TestMain.output_fp)

    def test_main(self):
        with self.assertRaises(consolidate.FormatException):
            # Should raise error since neither z nor a have all required keys
            argv = ["-i", self.mock_fwtc_dir.name, "-o", TestMain.output_fp]
            consolidate.main(argv)


class TestMain(unittest.TestCase):
    """End-to-end test case for main()."""

    output_fp = "/tmp/CONSOLIDATED.json"

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.maxDiff = None
        self.mock_fwtc_dir = (
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, "a.json")
        with open(a_json_fp, "w", encoding="utf-8") as a_json_file:
            a_json = collections.OrderedDict(
                {
                    "platform": "a",
                    "firmware_screen": 0.5,
                    "ec_capability": {
                        "adc_ectemp": True,
                        "arm": True,
                        "battery": False,
                        "cbi": False,
                        "charging": False,
                        "doubleboot": False,
                        "keyboard": False,
                        "lid": False,
                        "peci": False,
                        "smart_usb_charge": False,
                        "thermal": False,
                        "usb": True,
                        "usbpd_uart": False,
                        "x86": True,
                    },
                }
            )
            json.dump(a_json, a_json_file)
        z_json_fp = os.path.join(self.mock_fwtc_dir.name, "z.json")
        with open(z_json_fp, "w", encoding="utf-8") as z_json_file:
            z_json = collections.OrderedDict(
                {
                    "platform": "z",
                    "parent": "a",
                    "firmware_screen": 10,
                    "ec_capability": {  # override a:
                        "arm": False,
                        "keyboard": True,
                        "lid": True,
                        "default_true": False,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": False,
                        "wp_on_in_g3": False,
                        "rdd_off_in_g3": True,
                        "rdd_leakage": True,
                    },
                }
            )
            json.dump(z_json, z_json_file)
        b_json_fp = os.path.join(self.mock_fwtc_dir.name, "b.json")
        with open(b_json_fp, "w", encoding="utf-8") as b_json_file:
            b_json = collections.OrderedDict(
                {
                    "platform": "b",  # b<-z<-a
                    "parent": "z",
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": True,
                        "rdd_off_in_g3": False,
                    },
                    "minidiag_capability": {"event_log_launch_count": False},
                }
            )
            json.dump(b_json, b_json_file)
        defaults_json_fp = os.path.join(
            self.mock_fwtc_dir.name, "DEFAULTS.json"
        )
        with open(
            defaults_json_fp, "w", encoding="utf-8"
        ) as defaults_json_file:
            defaults_json = collections.OrderedDict(
                {
                    "platform": None,
                    "platform.DOC": "foo",
                    "firmware_screen": 42,
                    "parent": None,
                    "ec_capability": {
                        "adc_ectemp": None,
                        "arm": None,
                        "battery": None,
                        "cbi": None,
                        "charging": None,
                        "doubleboot": None,
                        "keyboard": None,
                        "lid": None,
                        "peci": None,
                        "smart_usb_charge": None,
                        "thermal": None,
                        "usb": None,
                        "usbpd_uart": None,
                        "x86": None,
                        "default_true": True,
                        "default_false": False,
                    },
                    "cr50_capability": {
                        "ec_hibernate_breaks_rdd": False,
                        "wp_on_in_g3": False,
                        "rdd_off_in_g3": False,
                        "rdd_leakage": False,
                    },
                    "minidiag_capability": {
                        "storage_self_test": True,
                        "event_log_launch_count": True,
                    },
                }
            )
            json.dump(defaults_json, defaults_json_file)

    def tearDown(self):
        """Delete output file and mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()
        if os.path.isfile(TestMain.output_fp):
            os.remove(TestMain.output_fp)

    def test_main(self):
        """Verify that the whole script works, end-to-end."""
        expected_str = """{
  "DEFAULTS": {
    "cr50_capability": [],
    "ec_capability": [
      "default_true"
    ],
    "firmware_screen": 42,
    "minidiag_capability": [
      "event_log_launch_count",
      "storage_self_test"
    ],
    "parent": null,
    "platform": null,
    "platform.DOC": "foo"
  },
  "a": {
    "cr50_capability": [],
    "ec_capability": [
      "adc_ectemp",
      "arm",
      "default_true",
      "usb",
      "x86"
    ],
    "firmware_screen": 0.5,
    "minidiag_capability": [
      "event_log_launch_count",
      "storage_self_test"
    ],
    "platform": "a"
  },
  "b": {
    "cr50_capability": [
      "ec_hibernate_breaks_rdd",
      "rdd_leakage"
    ],
    "ec_capability": [
      "adc_ectemp",
      "keyboard",
      "lid",
      "usb",
      "x86"
    ],
    "firmware_screen": 10,
    "minidiag_capability": [
      "storage_self_test"
    ],
    "parent": "z",
    "platform": "b"
  },
  "z": {
    "cr50_capability": [
      "rdd_leakage",
      "rdd_off_in_g3"
    ],
    "ec_capability": [
      "adc_ectemp",
      "keyboard",
      "lid",
      "usb",
      "x86"
    ],
    "firmware_screen": 10,
    "minidiag_capability": [
      "event_log_launch_count",
      "storage_self_test"
    ],
    "parent": "a",
    "platform": "z"
  }
}
"""

        # Run the script twice to verify idempotency.
        for _ in range(2):
            # Run the script.
            argv = ["-i", self.mock_fwtc_dir.name, "-o", TestMain.output_fp]
            consolidate.main(argv)

            # Verify the output.
            with open(TestMain.output_fp, encoding="utf-8") as output_file:
                output_contents = [
                    s.rstrip("\n") for s in output_file.readlines()
                ]
            expected_output = expected_str.splitlines()

            if expected_output != output_contents:
                self.fail(
                    "Expected output doesn't match actual output. Diff:\n"
                    + "\n".join(
                        difflib.unified_diff(
                            expected_output,
                            output_contents,
                            fromfile="expected",
                            tofile="actual",
                            lineterm="",
                        )
                    ),
                )

        # Verify the final output is read-only.
        with self.assertRaises(PermissionError):
            with open(TestMain.output_fp, "w", encoding="utf-8") as output_file:
                output_file.write("foo")


if __name__ == "__main__":
    unittest.main()
