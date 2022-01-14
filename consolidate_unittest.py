#!/usr/bin/env python3
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Unit tests for consolidate.py.

"""

import collections
import json
import os
import pathlib
import tempfile
import unittest

import consolidate


class TestParseArgs(unittest.TestCase):
    """Test case for parse_args()."""

    def setUp(self):
        """
        Change the current working directory.

        This will ensure that even if the script is run from elsewhere,
        input_dir arg still defaults to fw-testing-configs.
        """
        self.original_cwd = os.getcwd()
        os.chdir('/tmp')

    def tearDown(self):
        """Restore the original working directory."""
        os.chdir(self.original_cwd)

    def test_command_line_args(self):
        """Test with specified command-line args."""
        input_dir = 'foo'
        output_file = 'bar'
        argv = ['-i', input_dir, '-o', output_file]
        args = consolidate.parse_args(argv)
        self.assertEqual(args.input_dir, input_dir)
        self.assertEqual(args.output, output_file)

    def test_defaults(self):
        """Test with no command-line args."""
        args = consolidate.parse_args([])
        self.assertEqual(args.output, consolidate.DEFAULT_OUTPUT_FILEPATH)
        # Note: This assertion is not hermetic!
        self.assertTrue('fw-testing-configs' in args.input_dir)
        # Note: This assertion is not hermetic!
        self.assertTrue('DEFAULTS.json' in os.listdir(args.input_dir))


class TestGetPlatformNames(unittest.TestCase):
    """Test case for get_platform_names()."""

    def setUp(self):
        """Create mock fw-testing-configs directory."""
        self.mock_fwtc_dir = tempfile.TemporaryDirectory()
        mock_platform_names = ['z', 'a', 'b', 'DEFAULTS', 'CONSOLIDATED']
        for platform in mock_platform_names:
            mock_filepath = os.path.join(self.mock_fwtc_dir.name,
                                         platform + '.json')
            pathlib.Path(mock_filepath).touch()

    def tearDown(self):
        """Destroy mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()

    def test_get_platform_names(self):
        """
        Verify that platform names load in the correct order.

        The correct order is starting with DEFAULTS, then alphabetical.
        The .json file extension should not be included.
        """
        platforms = consolidate.get_platform_names(self.mock_fwtc_dir.name)
        self.assertEqual(platforms, ['DEFAULTS', 'a', 'b', 'z'])


class TestLoadJSON(unittest.TestCase):
    """Test case for load_json()."""

    def setUp(self):
        """Setup mock fw-testing-configs directory."""
        self.maxDiff = None
        self.mock_fwtc_dir = tempfile.TemporaryDirectory()
        a_filename = os.path.join(self.mock_fwtc_dir.name, 'a.json')
        with open(a_filename, 'w') as a_file:
            a_file.write('{\n' +
                         '\t"platform": "a",\n' +
                         '\t"ec_capability": {' +
                         '\t\t"adc_ectemp": false,\n' +
                         '\t\t"arm": false,\n' +
                         '\t\t"battery": false,\n' +
                         '\t\t"cbi": false,\n' +
                         '\t\t"charging": false,\n' +
                         '\t\t"doubleboot": false,\n' +
                         '\t\t"keyboard": false,\n' +
                         '\t\t"lid": false,\n' +
                         '\t\t"peci": false,\n' +
                         '\t\t"smart_usb_charge": false,\n' +
                         '\t\t"thermal": false,\n' +
                         '\t\t"usb": true,\n' +          # set as True for test
                         '\t\t"usbpd_uart": false,\n' +
                         '\t\t"x86": true\n' +           # set as True for test
                         '\t},\n' +
                         '\t"cr50_capability": {' +
                         '\t\t"ec_hibernate_breaks_rdd": false,\n' +
                         '\t\t"wp_on_in_g3": true,\n' +  # set as True for test
                         '\t\t"rdd_off_in_g3": false,\n' +
                         '\t\t"rdd_leakage": true\n' +   # set as True for test
                         '\t}\n' +
                         '}')
        defaults_filename = os.path.join(self.mock_fwtc_dir.name,
                                         'DEFAULTS.json')
        with open(defaults_filename, 'w') as defaults_file:
            defaults_file.write('{\n' +
                                '\t"platform": null,\n' +
                                '\t"platform_DOC": "foo",\n' +
                                '\t"ec_capability": {' +
                                '\t\t"adc_ectemp": null,\n' +
                                '\t\t"arm": null,\n' +
                                '\t\t"battery": null,\n' +
                                '\t\t"cbi": null,\n' +
                                '\t\t"charging": null,\n' +
                                '\t\t"doubleboot": null,\n' +
                                '\t\t"keyboard": null,\n' +
                                '\t\t"lid": null,\n' +
                                '\t\t"peci": null,\n' +
                                '\t\t"smart_usb_charge": null,\n' +
                                '\t\t"thermal": null,\n' +
                                '\t\t"usb": null,\n' +
                                '\t\t"usbpd_uart": null,\n' +
                                '\t\t"x86": null,\n' +
                                '\t\t"default_true": true,\n' +
                                '\t\t"default_false": false\n' +
                                '\t},\n' +
                                '\t"cr50_capability": {' +
                                '\t\t"ec_hibernate_breaks_rdd": null,\n' +
                                '\t\t"wp_on_in_g3": null,\n' +
                                '\t\t"rdd_off_in_g3": null,\n' +
                                '\t\t"rdd_leakage": null,\n' +
                                '\t\t"default_true": true,\n' +
                                '\t\t"default_false": false\n' +
                                '\t}\n' +
                                '}')

    def tearDown(self):
        self.mock_fwtc_dir.cleanup()

    def test_load_json(self):
        """Verify that we correctly load platform JSON contents."""
        expected = collections.OrderedDict()
        expected['DEFAULTS'] = collections.OrderedDict()
        expected['DEFAULTS']['platform'] = None
        expected['DEFAULTS']['platform_DOC'] = 'foo'
        expected['DEFAULTS']['ec_capability'] = ['default_true']
        expected['DEFAULTS']['cr50_capability'] = ['default_true']
        expected['a'] = collections.OrderedDict()
        expected['a']['platform'] = 'a'
        expected['a']['ec_capability'] = ['default_true', 'usb', 'x86']
        expected['a']['cr50_capability'] = ['default_true', 'rdd_leakage', 'wp_on_in_g3']
        actual = consolidate.load_json(self.mock_fwtc_dir.name,
                                       ['DEFAULTS', 'a'])
        self.assertEqual(actual, expected)


class TestWriteOutput(unittest.TestCase):
    """Test case for write_output()."""
    output_fp = '/tmp/CONSOLIDATED.json'

    def tearDown(self):
        """Clean up output_fp"""
        if os.path.isfile(TestWriteOutput.output_fp):
            os.remove(TestWriteOutput.output_fp)

    def test_write_output(self):
        """Verify that write_output writes JSON and sets to read-only."""
        # Run the function
        mock_json = collections.OrderedDict({'foo': 'bar', 'bar': 'baz'})
        consolidate.write_output(mock_json, TestWriteOutput.output_fp)

        # Verify file contents
        with open(TestWriteOutput.output_fp) as output_file:
            output_contents = output_file.readlines()
        expected = ['{\n',
                    '\t"foo": "bar",\n',
                    '\t"bar": "baz"\n',
                    '}']
        self.assertEqual(output_contents, expected)

        # Verify that file is read-only
        with self.assertRaises(PermissionError):
            with open(TestWriteOutput.output_fp, 'w') as output_file:
                output_file.write('foo')


class TestInvalidECCapability(unittest.TestCase):
    """Test case for invalid ec_capability configurations"""
    output_fp = '/tmp/CONSOLIDATED.json'

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.mock_fwtc_dir = tempfile.TemporaryDirectory()
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, 'a.json')
        with open(a_json_fp, 'w') as a_json_file:
            a_json = collections.OrderedDict({
                'platform': 'a',
                'firmware_screen': 0.5,
                'ec_capability': {
                    'adc_ectemp': True,
                    'arm': True,
                    'battery': False,
                    'cbi': False,
                    'charging': False,
                    'doubleboot': False,
                    'keyboard': False,
                    'lid': False,
                    'peci': False,
                    'smart_usb_charge': False,
                    'thermal': False,
                    'usb': True,
                    'usbpd_uart': False,
                    'x86': True
                },
                'cr50_capability': {
                    'ec_hibernate_breaks_rdd': True,
                    'wp_on_in_g3': True,
                    'rdd_off_in_g3': False,
                    'rdd_leakage': False
                }
            })
            json.dump(a_json, a_json_file)
        z_json_fp = os.path.join(self.mock_fwtc_dir.name, 'z.json')
        with open(z_json_fp, 'w') as z_json_file:
            z_json = collections.OrderedDict({'platform': 'z',
                                              'parent': 'a',
                                              'firmware_screen': 10,
                                              'ec_capability': {  # override a:
                                                  'arm': False,
                                                  'FAKE': True, # invalid
                                              },
                                              'cr50_capability': {
                                                  'wp_on_in_g3': False,
                                                  'rdd_off_in_g3': True,
                                              }
                                            })
            json.dump(z_json, z_json_file)
        defaults_json_fp = os.path.join(self.mock_fwtc_dir.name,
                                        'DEFAULTS.json')
        with open(defaults_json_fp, 'w') as defaults_json_file:
            defaults_json = collections.OrderedDict({
                'platform': None,
                'platform_DOC': 'foo',
                'ec_capability': {
                    'adc_ectemp': None,
                    'arm': None,
                    'battery': None,
                    'cbi': None,
                    'charging': None,
                    'doubleboot': None,
                    'keyboard': None,
                    'lid': None,
                    'peci': None,
                    'smart_usb_charge': None,
                    'thermal': None,
                    'usb': None,
                    'usbpd_uart': None,
                    'x86': None,
                    'default_true': True,
                    'default_false': False,
                },
                'cr50_capability': {
                    'ec_hibernate_breaks_rdd': None,
                    'wp_on_in_g3': None,
                    'rdd_off_in_g3': None,
                    'rdd_leakage': None,
                    'default_true': True,
                    'default_false': False,
                }
            })
            json.dump(defaults_json, defaults_json_file)

    def tearDown(self):
        """Delete output file and mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()
        if os.path.isfile(TestMain.output_fp):
            os.remove(TestMain.output_fp)

    def test_main(self):
        with self.assertRaises(consolidate.FormatException):
            # Should raise error since child has invalid capability
            argv = ['-i', self.mock_fwtc_dir.name, '-o', TestMain.output_fp]
            consolidate.main(argv)


class TestMissingECCapability(unittest.TestCase):
    """Test case for missing ec_capability configurations"""
    output_fp = '/tmp/CONSOLIDATED.json'

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.mock_fwtc_dir = tempfile.TemporaryDirectory()
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, 'a.json')
        with open(a_json_fp, 'w') as a_json_file:
            a_json = collections.OrderedDict({
                'platform': 'a',
                'firmware_screen': 0.5,
                'ec_capability': {
                    'adc_ectemp': True,
                    'arm': True,
                    # Removed battery, cbi keys
                    'charging': False,
                    'doubleboot': False,
                    'keyboard': False,
                    'lid': False,
                    'peci': False,
                    'smart_usb_charge': False,
                    'thermal': False,
                    'usb': True,
                    'usbpd_uart': False,
                    'x86': True
                },
                'cr50_capability': {
                    'ec_hibernate_breaks_rdd': True,
                    'wp_on_in_g3': True,
                    'rdd_off_in_g3': False,
                    'rdd_leakage': False
                }
            })
            json.dump(a_json, a_json_file)
        z_json_fp = os.path.join(self.mock_fwtc_dir.name, 'z.json')
        with open(z_json_fp, 'w') as z_json_file:
            z_json = collections.OrderedDict({'platform': 'z',
                                              'parent': 'a',
                                              'firmware_screen': 10,
                                              'ec_capability': {  # override a:
                                                  'arm': False,
                                                  'keyboard': True,
                                                  'lid': True,
                                              },
                                              'cr50_capability': {
                                                  'wp_on_in_g3': False,
                                                  'rdd_off_in_g3': True,
                                              }})
            json.dump(z_json, z_json_file)
        defaults_json_fp = os.path.join(self.mock_fwtc_dir.name,
                                        'DEFAULTS.json')
        with open(defaults_json_fp, 'w') as defaults_json_file:
            defaults_json = collections.OrderedDict({
                'platform': None,
                'platform_DOC': 'foo',
                'ec_capability': {
                    'adc_ectemp': None,
                    'arm': None,
                    'battery': None,
                    'cbi': None,
                    'charging': None,
                    'doubleboot': None,
                    'keyboard': None,
                    'lid': None,
                    'peci': None,
                    'smart_usb_charge': None,
                    'thermal': None,
                    'usb': None,
                    'usbpd_uart': None,
                    'x86': None,
                    'default_true': True,
                    'default_false': False,
                },
                'cr50_capability': {
                    'ec_hibernate_breaks_rdd': None,
                    'wp_on_in_g3': None,
                    'rdd_off_in_g3': None,
                    'rdd_leakage': None,
                    'default_true': True,
                    'default_false': False,
                }
            })
            json.dump(defaults_json, defaults_json_file)

    def tearDown(self):
        """Delete output file and mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()
        if os.path.isfile(TestMain.output_fp):
            os.remove(TestMain.output_fp)

    def test_main(self):
        with self.assertRaises(consolidate.FormatException):
            # Should raise error since neither z nor a have all required keys
            argv = ['-i', self.mock_fwtc_dir.name, '-o', TestMain.output_fp]
            consolidate.main(argv)


class TestInvalidCR50Capability(unittest.TestCase):
    """Test case for invalid cr50_capability configurations"""
    output_fp = '/tmp/CONSOLIDATED.json'

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.mock_fwtc_dir = tempfile.TemporaryDirectory()
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, 'a.json')
        with open(a_json_fp, 'w') as a_json_file:
            a_json = collections.OrderedDict({
                'platform': 'a',
                'firmware_screen': 0.5,
                'ec_capability': {
                    'adc_ectemp': True,
                    'arm': True,
                    'battery': False,
                    'cbi': False,
                    'charging': False,
                    'doubleboot': False,
                    'keyboard': False,
                    'lid': False,
                    'peci': False,
                    'smart_usb_charge': False,
                    'thermal': False,
                    'usb': True,
                    'usbpd_uart': False,
                    'x86': True
                },
                'cr50_capability': {
                    'FAKE': True,          # invalid cr50_capability
                    'wp_on_in_g3': True,
                    'rdd_off_in_g3': False,
                    'rdd_leakage': False
                }
            })
            json.dump(a_json, a_json_file)
        defaults_json_fp = os.path.join(self.mock_fwtc_dir.name,
                                        'DEFAULTS.json')
        with open(defaults_json_fp, 'w') as defaults_json_file:
            defaults_json = collections.OrderedDict({
                'platform': None,
                'platform_DOC': 'foo',
                'ec_capability': {
                    'adc_ectemp': None,
                    'arm': None,
                    'battery': None,
                    'cbi': None,
                    'charging': None,
                    'doubleboot': None,
                    'keyboard': None,
                    'lid': None,
                    'peci': None,
                    'smart_usb_charge': None,
                    'thermal': None,
                    'usb': None,
                    'usbpd_uart': None,
                    'x86': None,
                    'default_true': True,
                    'default_false': False,
                },
                'cr50_capability': {
                    'ec_hibernate_breaks_rdd': None,
                    'wp_on_in_g3': None,
                    'rdd_off_in_g3': None,
                    'rdd_leakage': None,
                    'default_true': True,
                    'default_false': False,
                }
            })
            json.dump(defaults_json, defaults_json_file)

    def tearDown(self):
        """Delete output file and mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()
        if os.path.isfile(TestMain.output_fp):
            os.remove(TestMain.output_fp)

    def test_main(self):
        with self.assertRaises(consolidate.FormatException):
            # Should raise error since child has invalid capability
            argv = ['-i', self.mock_fwtc_dir.name, '-o', TestMain.output_fp]
            consolidate.main(argv)


class TestMissingCR50Capability(unittest.TestCase):
    """Test case for missing cr_50 configurations"""
    output_fp = '/tmp/CONSOLIDATED.json'

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.mock_fwtc_dir = tempfile.TemporaryDirectory()
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, 'a.json')
        with open(a_json_fp, 'w') as a_json_file:
            a_json = collections.OrderedDict({
                'platform': 'a',
                'firmware_screen': 0.5,
                'ec_capability': {
                    'adc_ectemp': True,
                    'arm': True,
                    'battery': False,
                    'cbi': False,
                    'charging': False,
                    'doubleboot': False,
                    'keyboard': False,
                    'lid': False,
                    'peci': False,
                    'smart_usb_charge': False,
                    'thermal': False,
                    'usb': True,
                    'usbpd_uart': False,
                    'x86': True
                },
                'cr50_capability': {
                    'ec_hibernate_breaks_rdd': True,
                    'rdd_off_in_g3': False,  # 'wp_on_in_g3' removed
                    'rdd_leakage': False
                }
            })
            json.dump(a_json, a_json_file)
        defaults_json_fp = os.path.join(self.mock_fwtc_dir.name,
                                        'DEFAULTS.json')
        with open(defaults_json_fp, 'w') as defaults_json_file:
            defaults_json = collections.OrderedDict({
                'platform': None,
                'platform_DOC': 'foo',
                'ec_capability': {
                    'adc_ectemp': None,
                    'arm': None,
                    'battery': None,
                    'cbi': None,
                    'charging': None,
                    'doubleboot': None,
                    'keyboard': None,
                    'lid': None,
                    'peci': None,
                    'smart_usb_charge': None,
                    'thermal': None,
                    'usb': None,
                    'usbpd_uart': None,
                    'x86': None,
                    'default_true': True,
                    'default_false': False,
                },
                'cr50_capability': {
                    'ec_hibernate_breaks_rdd': None,
                    'wp_on_in_g3': None,
                    'rdd_off_in_g3': None,
                    'rdd_leakage': None,
                    'default_true': True,
                    'default_false': False,
                }
            })
            json.dump(defaults_json, defaults_json_file)

    def tearDown(self):
        """Delete output file and mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()
        if os.path.isfile(TestMain.output_fp):
            os.remove(TestMain.output_fp)

    def test_main(self):
        with self.assertRaises(consolidate.FormatException):
            # Should raise error since neither z nor a have all required keys
            argv = ['-i', self.mock_fwtc_dir.name, '-o', TestMain.output_fp]
            consolidate.main(argv)


class TestMain(unittest.TestCase):
    """End-to-end test case for main()."""
    output_fp = '/tmp/CONSOLIDATED.json'

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.maxDiff = None
        self.mock_fwtc_dir = tempfile.TemporaryDirectory()
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, 'a.json')
        with open(a_json_fp, 'w') as a_json_file:
            a_json = collections.OrderedDict({
                'platform': 'a',
                'firmware_screen': 0.5,
                'ec_capability': {
                    'adc_ectemp': True,
                    'arm': True,
                    'battery': False,
                    'cbi': False,
                    'charging': False,
                    'doubleboot': False,
                    'keyboard': False,
                    'lid': False,
                    'peci': False,
                    'smart_usb_charge': False,
                    'thermal': False,
                    'usb': True,
                    'usbpd_uart': False,
                    'x86': True
                },
            })
            json.dump(a_json, a_json_file)
        z_json_fp = os.path.join(self.mock_fwtc_dir.name, 'z.json')
        with open(z_json_fp, 'w') as z_json_file:
            z_json = collections.OrderedDict({'platform': 'z',
                                              'parent': 'a',
                                              'firmware_screen': 10,
                                              'ec_capability': {  # override a:
                                                  'arm': False,
                                                  'keyboard': True,
                                                  'lid': True,
                                                  'default_true': False,
                                              },
                                              'cr50_capability': {
                                                'ec_hibernate_breaks_rdd': False,
                                                'wp_on_in_g3': False,
                                                'rdd_off_in_g3': True,
                                                'rdd_leakage': True,
                                              }
                                            })
            json.dump(z_json, z_json_file)
        b_json_fp = os.path.join(self.mock_fwtc_dir.name, 'b.json')
        with open(b_json_fp, 'w') as b_json_file:
            b_json = collections.OrderedDict({'platform': 'b', # b<-z<-a
                                              'parent': 'z',
                                              'cr50_capability': {
                                                'ec_hibernate_breaks_rdd': True,
                                                'rdd_off_in_g3': False,
                                              },
                                            })
            json.dump(b_json, b_json_file)
        defaults_json_fp = os.path.join(self.mock_fwtc_dir.name,
                                        'DEFAULTS.json')
        with open(defaults_json_fp, 'w') as defaults_json_file:
            defaults_json = collections.OrderedDict({
                'platform': None,
                'platform_DOC': 'foo',
                'ec_capability': {
                        'adc_ectemp': None,
                        'arm': None,
                        'battery': None,
                        'cbi': None,
                        'charging': None,
                        'doubleboot': None,
                        'keyboard': None,
                        'lid': None,
                        'peci': None,
                        'smart_usb_charge': None,
                        'thermal': None,
                        'usb': None,
                        'usbpd_uart': None,
                        'x86': None,
                        'default_true': True,
                        'default_false': False,
                },
                'cr50_capability': {
                    'ec_hibernate_breaks_rdd': False,
                    'wp_on_in_g3': False,
                    'rdd_off_in_g3': False,
                    'rdd_leakage': False,
                }
            })
            json.dump(defaults_json, defaults_json_file)

    def tearDown(self):
        """Delete output file and mock fw-testing-configs directory."""
        self.mock_fwtc_dir.cleanup()
        if os.path.isfile(TestMain.output_fp):
            os.remove(TestMain.output_fp)

    def test_main(self):
        """Verify that the whole script works, end-to-end."""
        expected_output = ['{\n',
                           '\t"DEFAULTS": {\n',
                           '\t\t"platform": null,\n',
                           '\t\t"platform_DOC": "foo",\n',
                           '\t\t"ec_capability": [\n',
                           '\t\t\t"default_true"\n',
                           '\t\t],\n',
                           '\t\t"cr50_capability": []\n',
                           '\t},\n',
                           '\t"a": {\n',
                           '\t\t"platform": "a",\n',
                           '\t\t"firmware_screen": 0.5,\n',
                           '\t\t"ec_capability": [\n',
                           '\t\t\t"adc_ectemp",\n',
                           '\t\t\t"arm",\n',
                           '\t\t\t"default_true",\n',
                           '\t\t\t"usb",\n',
                           '\t\t\t"x86"\n',
                           '\t\t],\n',
                           '\t\t"cr50_capability": []\n',
                           '\t},\n',
                           '\t"b": {\n',
                           '\t\t"platform": "b",\n',
                           '\t\t"parent": "z",\n',
                           '\t\t"cr50_capability": [\n',
                           '\t\t\t"ec_hibernate_breaks_rdd",\n',
                           '\t\t\t"rdd_leakage"\n',
                           '\t\t],\n',
                           '\t\t"ec_capability": [\n',
                           '\t\t\t"adc_ectemp",\n', # inherit from a
                           '\t\t\t"keyboard",\n', # specific for z
                           '\t\t\t"lid",\n', # specific for z
                           '\t\t\t"usb",\n', # inherited from a
                           '\t\t\t"x86"\n', # inherited from a
                           '\t\t]\n',
                           '\t},\n',
                           '\t"z": {\n',
                           '\t\t"platform": "z",\n',
                           '\t\t"parent": "a",\n',
                           '\t\t"firmware_screen": 10,\n',
                           '\t\t"ec_capability": [\n',
                           '\t\t\t"adc_ectemp",\n', # inherit from a
                           '\t\t\t"keyboard",\n', # specific for z
                           '\t\t\t"lid",\n', # specific for z
                           '\t\t\t"usb",\n', # inherited from a
                           '\t\t\t"x86"\n', # inherited from a
                           '\t\t],\n',
                           '\t\t"cr50_capability": [\n',
                           '\t\t\t"rdd_leakage",\n',
                           '\t\t\t"rdd_off_in_g3"\n',
                           '\t\t]\n',
                           '\t}\n',
                           '}']

        # Run the script twice to verify idempotency.
        for _ in range(2):
            # Run the script.
            argv = ['-i', self.mock_fwtc_dir.name, '-o', TestMain.output_fp]
            consolidate.main(argv)

            # Verify the output.
            with open(TestMain.output_fp) as output_file:
                output_contents = output_file.readlines()

            self.assertEqual(expected_output, output_contents)

        # Verify the final output is read-only.
        with self.assertRaises(PermissionError):
            with open(TestMain.output_fp, 'w') as output_file:
                output_file.write('foo')


if __name__ == '__main__':
    unittest.main()
