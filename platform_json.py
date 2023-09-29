#!/usr/bin/env python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Print one fully-calculated fw-testing-config to stdout.

This script takes one platform name (and optionally a model name) as inputs,
calculates the full config for that platform, and prints the results as
plaintext JSON.

The full config is calculated based on the fw-testing-configs inheritance
model.  Each platform config has an optional "parent" attribute. For each
config field, if the platform does not explicitly set a value for that field,
then the value is instead inherited from the parent config. This inheritance
can be recursive: the parent may have a parent, and so on. At the top of the
inheritance tree (when parent is None), any remaining fields inherit their
values from DEFAULTS. Also, if the platform has a "models" attribute matching
the passed-in model name, then its field-value pairs override everything else.
"""

import argparse
import collections
import json
import os
import re
import sys


# Regexes matching fields which describe config metadata: that is, they do not
# contain actual config information.  When calculating the final config, fields
# matching any of these regexes will be ignored.
META_FIELD_REGEXES = (re.compile(r"^models$"), re.compile(r"\.DOC$"))


class PlatformNotFoundError(AttributeError):
    """Error class for when the requested platform name is not found."""


class FieldNotFoundError(AttributeError):
    """Error class for when the requested field name is not found."""


def parse_args(argv):
    """Determine input dir and output file from command-line args.

    Args:
        argv: List of command-line args, excluding the invoked script.
              Typically, this should be set to sys.argv[1:].

    Returns:
        An argparse.Namespace with the following attributes:
            condense_output: A bool determining whether to remove pretty
                whitespace from the script's final output.
            consolidated: The filepath to CONSOLIDATED.json
            field: If specified, then only this field's value will be printed.
            platform: The name of the board whose config should be calculated
            model: The name of the model for the board

    Raises:
        ValueError: If the passed-in platform name ends in '.json'
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "platform",
        help="The platform name to calculate a config for. "
        'Should not include ".json" suffix.',
    )
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="The model name of the board. If not specified, "
        "then no model overrides will be used.",
    )
    parser.add_argument(
        "-f",
        "--field",
        default=None,
        help="If specified, only print this field's value.",
    )
    parser.add_argument(
        "-c",
        "--consolidated",
        default="CONSOLIDATED.json",
        help="The filepath to CONSOLIDATED.json",
    )
    parser.add_argument(
        "--condense-output",
        action="store_true",
        help="Print the output without pretty whitespace.",
    )
    args = parser.parse_args(argv)
    return args


def calculate_field_value(consolidated_json, field, platform, model=None):
    """Calculate a platform's ultimate value for a single field.

    Args:
        consolidated_json: The key-value contents of CONSOLIDATED.json.
        field: The name of the JSON field to calculate.
        platform: The name of the platform to calculate for.  If the
            platform does not define the field, then recursively check its
            parent's config (or DEFAULTS).
        model: The name of the model to check overrides for.

    Raises:
        PlatformNotFoundError: If platform is not in consolidated_json.
    """
    if platform not in consolidated_json:
        raise PlatformNotFoundError(platform)

    # Model overrides are most important.
    # Not all models have config overrides, so it's OK for the model name not
    # to be present in models_json.
    models_json = consolidated_json[platform].get("models", {})
    if field in models_json.get(model, {}):
        return models_json[model][field]

    # Then check if the platform explicitly defines the value.
    if field in consolidated_json[platform]:
        return consolidated_json[platform][field]

    # Finally, inherit from the parent (or DEFAULTS).
    # The DEFAULTS config contains every field name, so this will terminate the
    # recursion.
    parent = consolidated_json[platform].get("parent", "DEFAULTS")
    return calculate_field_value(consolidated_json, field, parent, model)


def load_consolidated_json(consolidated_fp):
    """Return the contents of consolidated_fp as a Python object."""
    if not os.path.isfile(consolidated_fp):
        raise FileNotFoundError(consolidated_fp)
    with open(consolidated_fp, encoding="utf-8") as consolidated_file:
        return json.load(consolidated_file)


def calculate_config(platform, model, consolidated_json):
    """Calculate a platform's ultimate config values for all fields.

    Args:
        platform: The name of the platform to calculate values for.
        model: The name of the model to check for overrides.
        consolidated_json: The full json dict for all platforms.
    """
    final_json = collections.OrderedDict()
    for field in consolidated_json["DEFAULTS"]:
        if any(regex.search(field) for regex in META_FIELD_REGEXES):
            continue
        value = calculate_field_value(consolidated_json, field, platform, model)
        final_json[field] = value
    return final_json


def main(argv):
    """Parse command-line args and print a JSON config to stdout.

    Args:
        argv: List of command-line args, excluding the invoked script.
              Typically, this should be set to sys.argv[1:].
    """
    args = parse_args(argv)
    consolidated_json = load_consolidated_json(args.consolidated)
    config_json = calculate_config(args.platform, args.model, consolidated_json)
    if args.field is None:
        # indent=None means no newlines/indents in stringified JSON.
        # indent=4 means 4-space indents.
        indent = None if args.condense_output else 4
        output = json.dumps(config_json, indent=indent)
    elif args.field not in config_json:
        raise FieldNotFoundError(args.field)
    else:
        output = config_json[args.field]
    print(output, end="" if args.condense_output else "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
