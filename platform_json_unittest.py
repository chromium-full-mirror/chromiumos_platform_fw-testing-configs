#!/usr/bin/env python3
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Unit tests for platform_json.py

"""

import os
import tempfile
import unittest

import platform_json

MOCK_CONSOLIDATED_JSON_CONTENTS = \
'''{
    "DEFAULTS": {
        "platform": null,
        "parent": null,
        "field1": 5,
        "field2": 5,
        "field3": 5,
        "field4": 5
    },
    "my_platform": {
        "platform": "my_platform",
        "parent": "my_parent",
        "field1": 1,
        "models": {
            "my_model": {
                "field1": 4
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
}'''

class InheritanceTestCase(unittest.TestCase):
    """Ensure that all levels of inheritance are handled correctly"""

    def setUp(self):
        """Write mock JSON to a temporary file"""
        _, self.mock_filepath = tempfile.mkstemp()
        with open(self.mock_filepath, 'w') as mock_file:
            mock_file.write(MOCK_CONSOLIDATED_JSON_CONTENTS)

    def runTest(self):  # pylint:disable=invalid-name
        """Load platform config and check that it looks correct"""
        my_platform = platform_json.calculate_platform_json('my_platform',
                                                            None,
                                                            self.mock_filepath)
        self.assertEqual(my_platform['field1'], 1) # No inheritance
        self.assertEqual(my_platform['field2'], 2) # Direct inheritance
        self.assertEqual(my_platform['field3'], 3) # Recursive inheritance
        self.assertEqual(my_platform['field4'], 5) # Inherit from DEFAULTS
        my_model = platform_json.calculate_platform_json('my_platform',
                                                         'my_model',
                                                         self.mock_filepath)
        self.assertEqual(my_model['field1'], 4) # Model override
        self.assertEqual(my_model['field2'], 2) # Everything else is the same
        self.assertEqual(my_model['field3'], 3)
        self.assertEqual(my_model['field4'], 5)


    def tearDown(self):
        """Dsetroy the mock JSON file"""
        os.remove(self.mock_filepath)


if __name__ == '__main__':
    unittest.main()
