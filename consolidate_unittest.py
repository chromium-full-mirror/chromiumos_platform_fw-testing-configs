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
        args = consolidate.parse_args()
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
        self.mock_fwtc_dir = tempfile.TemporaryDirectory()
        a_filename = os.path.join(self.mock_fwtc_dir.name, 'a.json')
        with open(a_filename, 'w') as a_file:
            a_file.write('{\n' +
                         '\t"platform": "a",\n' +
                         '\t"ec_capability": [\n' +
                         '\t\t"usb",\n'
                         '\t\t"x86"\n' +
                         '\t]\n' +
                         '}')
        defaults_filename = os.path.join(self.mock_fwtc_dir.name,
                                         'DEFAULTS.json')
        with open(defaults_filename, 'w') as defaults_file:
            defaults_file.write('{\n' +
                                '\t"platform": null,\n' +
                                '\t"platform_DOC": "foo",\n' +
                                '\t"ec_capability": []\n' +
                                '}')

    def tearDown(self):
        self.mock_fwtc_dir.cleanup()

    def test_load_json(self):
        """Verify that we correctly load platform JSON contents."""
        expected = collections.OrderedDict()
        expected['DEFAULTS'] = collections.OrderedDict()
        expected['DEFAULTS']['platform'] = None
        expected['DEFAULTS']['platform_DOC'] = 'foo'
        expected['DEFAULTS']['ec_capability'] = []
        expected['a'] = collections.OrderedDict()
        expected['a']['platform'] = 'a'
        expected['a']['ec_capability'] = ['usb', 'x86']
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


class TestMain(unittest.TestCase):
    """End-to-end test case for main()."""
    output_fp = '/tmp/CONSOLIDATED.json'

    def setUp(self):
        """Create and populate mock fw-testing-configs directory."""
        self.mock_fwtc_dir = tempfile.TemporaryDirectory()
        a_json_fp = os.path.join(self.mock_fwtc_dir.name, 'a.json')
        with open(a_json_fp, 'w') as a_json_file:
            a_json = collections.OrderedDict({'platform': 'a',
                                              'firmware_screen': 0.5,
                                              'ec_capability': ['usb', 'x86']})
            json.dump(a_json, a_json_file)
        z_json_fp = os.path.join(self.mock_fwtc_dir.name, 'z.json')
        with open(z_json_fp, 'w') as z_json_file:
            z_json = collections.OrderedDict({'platform': 'z',
                                              'parent': 'a',
                                              'firmware_screen': 10})
            json.dump(z_json, z_json_file)
        defaults_json_fp = os.path.join(self.mock_fwtc_dir.name,
                                        'DEFAULTS.json')
        with open(defaults_json_fp, 'w') as defaults_json_file:
            defaults_json = collections.OrderedDict({'platform': None,
                                                     'platform_DOC': 'foo',
                                                     'ec_capability': []})
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
                           '\t\t"ec_capability": []\n',
                           '\t},\n',
                           '\t"a": {\n',
                           '\t\t"platform": "a",\n',
                           '\t\t"firmware_screen": 0.5,\n',
                           '\t\t"ec_capability": [\n',
                           '\t\t\t"usb",\n',
                           '\t\t\t"x86"\n',
                           '\t\t]\n',
                           '\t},\n',
                           '\t"z": {\n',
                           '\t\t"platform": "z",\n',
                           '\t\t"parent": "a",\n',
                           '\t\t"firmware_screen": 10\n',
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
            self.assertEqual(output_contents, expected_output)

        # Verify the final output is read-only.
        with self.assertRaises(PermissionError):
            with open(TestMain.output_fp, 'w') as output_file:
                output_file.write('foo')


if __name__ == '__main__':
    unittest.main()
