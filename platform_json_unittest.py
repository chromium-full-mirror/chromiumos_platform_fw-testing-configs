#!/usr/bin/env python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for platform_json.py"""

import collections
import io
import json
import os
import sys
import tempfile
import unittest

import platform_json


MOCK_CONSOLIDATED_JSON_CONTENTS = """{
    "DEFAULTS": {
        "platform": null,
        "parent": null,
        "field1": 5,
        "field2": 5,
        "field3": 5,
        "field4": 5,
        "fieldArray": [
            "elem5"
        ]
    },
    "my_platform": {
        "platform": "my_platform",
        "parent": "my_parent",
        "field1": 1,
        "fieldArray": [
            "elem1",
            "elem2"
        ],
        "models": {
            "my_model": {
                "field1": 4
            },
            "my_model2": {
                "field2": 4
            }
        }
    },
    "my_parent": {
        "platform": "my_parent",
        "parent": "my_grandparent",
        "field1": 2,
        "field2": 2
    },
    "my_grandparent": {
        "platform": "my_grandparent",
        "field1": 3,
        "field2": 3,
        "field3": 3
    }
}"""


def _run_main(argv):
    """Run platform_json.main(argv), capturing and returning stdout."""
    original_stdout = sys.stdout
    capture_io = io.StringIO()
    sys.stdout = capture_io
    try:
        platform_json.main(argv)
        return capture_io.getvalue()
    finally:
        capture_io.close()
        sys.stdout = original_stdout


class AbstractMockConfigTestCase:
    """Parent class to handle setup and teardown of mock configs."""

    def setUp(self):  # pylint:disable=invalid-name
        """Write mock JSON to a temporary file"""
        _, self.mock_filepath = tempfile.mkstemp()
        with open(self.mock_filepath, "w", encoding="utf-8") as mock_file:
            mock_file.write(MOCK_CONSOLIDATED_JSON_CONTENTS)

    def tearDown(self):  # pylint:disable=invalid-name
        """Destroy the mock JSON file"""
        os.remove(self.mock_filepath)


class InheritanceTestCase(AbstractMockConfigTestCase, unittest.TestCase):
    """Ensure that all levels of inheritance are handled correctly"""

    def runTest(self):  # pylint:disable=invalid-name
        """Load platform config and check that it looks correct"""
        consolidated_json = platform_json.load_consolidated_json(
            self.mock_filepath
        )
        my_platform = platform_json.calculate_config(
            "my_platform", None, consolidated_json
        )
        self.assertEqual(my_platform["field1"], 1)  # No inheritance
        self.assertEqual(my_platform["field2"], 2)  # Direct inheritance
        self.assertEqual(my_platform["field3"], 3)  # Recursive inheritance
        self.assertEqual(my_platform["field4"], 5)  # Inherit from DEFAULTS
        my_model = platform_json.calculate_config(
            "my_platform", "my_model", consolidated_json
        )
        self.assertEqual(my_model["field1"], 4)  # Model override
        self.assertEqual(my_model["field2"], 2)  # Everything else is the same
        self.assertEqual(my_model["field3"], 3)
        self.assertEqual(my_model["field4"], 5)


class EndToEndPlatformTestCase(AbstractMockConfigTestCase, unittest.TestCase):
    """End-to-end testing for specifying the platform name."""

    def runTest(self):  # pylint: disable=invalid-name
        """Main test logic"""
        # Basic platform specification
        argv = ["my_platform", "-c", self.mock_filepath]
        expected_json = collections.OrderedDict(
            {
                "platform": "my_platform",
                "parent": "my_parent",
                "field1": 1,
                "field2": 2,
                "field3": 3,
                "field4": 5,
                "fieldArray": [
                    "elem1",
                    "elem2",
                ],
            }
        )
        expected_output = json.dumps(expected_json, indent=4) + "\n"
        self.assertEqual(_run_main(argv), expected_output)

        # Condensed output
        argv.append("--condense-output")
        expected_output = json.dumps(expected_json, indent=None)
        self.assertEqual(_run_main(argv), expected_output)

        # Non-existent platform should raise an error
        argv = ["fake_platform", "-c", self.mock_filepath]
        with self.assertRaises(platform_json.PlatformNotFoundError):
            _run_main(argv)


class EndToEndFieldTestCase(AbstractMockConfigTestCase, unittest.TestCase):
    """End-to-end testing for specifying the field name."""

    def runTest(self):  # pylint: disable=invalid-name
        """Main test logic"""
        # Basic field specification
        argv = ["my_platform", "-f", "field1", "-c", self.mock_filepath]
        self.assertEqual(_run_main(argv), "1\n")

        # Condensed output should yield no newline
        argv.append("--condense-output")
        self.assertEqual(_run_main(argv), "1")

        # Non-existent field should raise an error
        argv = ["my_platform", "-f", "fake_field", "-c", self.mock_filepath]
        with self.assertRaises(platform_json.FieldNotFoundError):
            _run_main(argv)


if __name__ == "__main__":
    unittest.main()
