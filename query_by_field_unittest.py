#!/usr/bin/env python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for query_by_field.py"""

import io
import sys
import unittest

import platform_json_unittest
import query_by_field


def _run_main(argv):
    """Run platform_json.main(argv), capturing and returning stdout."""
    original_stdout = sys.stdout
    capture_io = io.StringIO()
    sys.stdout = capture_io
    try:
        query_by_field.main(argv)
        return capture_io.getvalue()
    finally:
        capture_io.close()
        sys.stdout = original_stdout


class SingleOperatorTestCase(
    platform_json_unittest.AbstractMockConfigTestCase, unittest.TestCase
):
    """Test-case for using a single operator of each type."""

    def runTest(self):  # pylint: disable=invalid-name
        """Test each operator in isolation."""
        # Equality operator ('=')
        argv = ["field1=5", "-c", self.mock_filepath]
        expected = "DEFAULTS\n"
        self.assertEqual(_run_main(argv), expected)

        # Inequality operator ('!=')
        argv = ["field1!=5", "-c", self.mock_filepath]
        expected = "my_platform\nmy_parent\nmy_grandparent\n"
        self.assertEqual(_run_main(argv), expected)

        # Array membership operator (':')
        argv = ["fieldArray:elem2", "-c", self.mock_filepath]
        expected = "my_platform\n"
        self.assertEqual(_run_main(argv), expected)

        # Array non-membership operator ('!:')
        argv = ["fieldArray!:elem5", "-c", self.mock_filepath]
        expected = "my_platform\n"
        self.assertEqual(_run_main(argv), expected)

        # Numeric less-than operator ('<')
        argv = ["field1<2", "-c", self.mock_filepath]
        expected = "my_platform (except my_model)\n"
        self.assertEqual(_run_main(argv), expected)

        # Numeric less-than-or-equal operator ('<=')
        argv = ["field1<=2", "-c", self.mock_filepath]
        expected = "my_platform (except my_model)\nmy_parent\n"
        self.assertEqual(_run_main(argv), expected)

        # Numeric greater-than operator ('>')
        argv = ["field1>4", "-c", self.mock_filepath]
        expected = "DEFAULTS\n"
        self.assertEqual(_run_main(argv), expected)

        # Numeric greater-than-or-equal operator ('>=')
        argv = ["field1>=4", "-c", self.mock_filepath]
        expected = "DEFAULTS\nmy_platform (only my_model)\n"
        self.assertEqual(_run_main(argv), expected)


class OperatorTypeMismatchTestCase(
    platform_json_unittest.AbstractMockConfigTestCase, unittest.TestCase
):
    """Test-case for exceptions being raised for operator-type mismatches."""

    def runTest(self):  # pylint: disable=invalid-name
        """Test each operator which can have invalid types."""
        # Array operators only make sense with array fields.
        for operator in (":", "!:"):
            query = "field1%s1" % operator
            argv = [query, "-c", self.mock_filepath]
            with self.assertRaises(query_by_field.NotIterableError):
                _run_main(argv)

        # Numeric operators only make sense with numeric fields.
        for operator in ("<", "<=", ">", ">="):
            config_value_is_array = "fieldArray%s1"
            config_value_is_string = "platform%s1"
            expected_value_is_string = "field1%sfoo"
            for fmt in (
                config_value_is_array,
                config_value_is_string,
                expected_value_is_string,
            ):
                query = fmt % operator
                argv = [query, "-c", self.mock_filepath]
                with self.assertRaises(query_by_field.NotNumericError):
                    _run_main(argv)


class MultipleOperatorsTestCase(
    platform_json_unittest.AbstractMockConfigTestCase, unittest.TestCase
):
    """Test-case for using multiple operators."""

    def runTest(self):  # pylint: disable=invalid-name
        """Test using multiple operators."""
        argv = ["field1!=1", "field1!=4", "-c", self.mock_filepath]
        expected = "DEFAULTS\nmy_parent\nmy_grandparent\n"
        self.assertEqual(_run_main(argv), expected)


class ModelExceptionsTestCase(
    platform_json_unittest.AbstractMockConfigTestCase, unittest.TestCase
):
    """Test-case for when model overrides change whether a platform matches."""

    def runTest(self):  # pylint: disable=invalid-name
        """Test all variants of model exceptions."""
        # Check for when a platform does not match, except for one model
        argv = ["field1=4", "-c", self.mock_filepath]
        expected = "my_platform (only my_model)\n"
        self.assertEqual(_run_main(argv), expected)

        # Check for when a platform matches, except for one model
        argv = ["field1=1", "-c", self.mock_filepath]
        expected = "my_platform (except my_model)\n"
        self.assertEqual(_run_main(argv), expected)

        # Check for multiple model exceptions
        argv = ["field1=1", "field2=2", "-c", self.mock_filepath]
        expected = "my_platform (except my_model, my_model2)\n"
        self.assertEqual(_run_main(argv), expected)


class NoMatchesTestCase(
    platform_json_unittest.AbstractMockConfigTestCase, unittest.TestCase
):
    """Test-case for when no platforms match the query."""

    def runTest(self):  # pylint: disable=invalid-name
        """Run script with a bogus query."""
        argv = ["field1=1337", "-c", self.mock_filepath]
        expected = "No platforms matched.\n"
        self.assertEqual(_run_main(argv), expected)


if __name__ == "__main__":
    unittest.main()
