#!/usr/bin/env python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Consolidate platform-specific data into CONSOLIDATE.json.

This script consolidates all the platform-specific config data into one file.
This enables test libraries to only rely on a single file.

The resulting file contains a single JSON object whose keys are the platform
names and whose values are the contents of that platform's original .json file.
The platforms are sorted alphabetically by name, with DEFAULTS first. Within
each platform, the order of keys is preserved from the original .json file.

Design doc: go/consolidate-fwtc
"""

import argparse
import collections
import json
import logging
import os
import stat
import sys


DEFAULT_OUTPUT_FILEPATH = "CONSOLIDATED.json"


class FormatException(Exception):
    """An exception thrown when the json is invalid."""

    def __init__(self, message, platform=None, model=None, field=None):
        if not message:
            message = "Formatting issue in platform json"
        if platform:
            message += f", in platform {platform}"
        if model:
            message += f", in model {model}"
        if field:
            message += f", in field {field}"
        message += "!"
        super().__init__(message)


def parse_args(argv=None):
    """Determine input dir and output file from command-line args.

    Args:
        argv: List of command-line args, excluding the invoked script.
              Typically, this should be set to sys.argv[1:].

    Returns:
        An argparse.Namespace with two attributes:
            input_dir: The directory containing fw-testing-configs JSON files
            output: The filepath where the final JSON output should be written
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input-dir",
        help="Directory with fw-testing-configs JSON files",
        default=os.path.dirname(os.path.realpath(__file__)),
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Filepath to write output to",
        default=DEFAULT_OUTPUT_FILEPATH,
    )
    return parser.parse_args(argv)


def get_platform_names(fwtc_dir):
    """Create a list of platforms with JSON files.

    Args:
        fwtc_dir: The fw-testing-configs directory containing platform JSON
        files.

    Returns:
        A list of strings representing the names of platforms which have JSON
        files in fwtc_dir, starting with DEFAULTS and then alphabetically.
        These names do not include .json.
    """
    platforms = []
    for fname in os.listdir(fwtc_dir):
        platform, ext = os.path.splitext(fname)
        if ext != ".json":
            continue
        elif platform in ("DEFAULTS", "CONSOLIDATED"):
            continue
        platforms.append(platform)
    platforms.sort()
    platforms = ["DEFAULTS"] + platforms
    return platforms


def load_json(fwtc_dir, platforms):
    """Create an OrderedDict of {platform_name: json_contents}.

    Args:
        fwtc_dir: The fw-testing-configs directory containing platform JSON
        files.
        platforms: A sorted list of names which have JSON files in fwtc_dir.

    Returns:
        An OrderedDict whose keys are platforms in the same order as in the
        passed-in param, and whose values OrderedDicts representing the contents
        of that platform's corresponding ${PLATFORM}.json file.
    """
    consolidated = collections.OrderedDict()
    for platform in platforms:
        json_path = os.path.join(fwtc_dir, platform + ".json")
        with open(json_path, encoding="utf-8") as json_file:
            try:
                j = json.load(
                    json_file, object_pairs_hook=collections.OrderedDict
                )
            except json.decoder.JSONDecodeError as e:
                raise FormatException(f"error decoding file {json_path}") from e
        consolidated[platform] = j
    check_parent_cycles(consolidated)
    detect_invalid_fields(consolidated)
    reformat_capability_map(consolidated, "ec_capability")
    reformat_capability_map(consolidated, "cr50_capability")
    reformat_capability_map(consolidated, "minidiag_capability")
    copy_parent_data(consolidated)
    return consolidated


def check_parent_cycles(consolidated):
    """Check for cycles in the parent field references.

    Args:
        consolidated: Dict containing configs for each platform JSON file.

    Returns:
        None
    """
    for platform in consolidated:
        curr_plat = platform
        seen = {platform}
        while True:
            curr_plat = consolidated[curr_plat].get("parent") or "DEFAULTS"

            # Check that there is no cycle of inheritance
            if curr_plat not in seen:
                seen.add(curr_plat)
            elif curr_plat == "DEFAULTS":
                break
            else:
                raise FormatException(
                    "Circular parent from platform json",
                    platform=platform,
                    field="parent",
                )


def reformat_capability_map(consolidated, cap_field):
    """Reformat {cap_field} from map to list as expected in consolidated dict.

    Based on explicitly defined {cap_field} and {cap_field} of parent
    platforms.

    Args:
        consolidated: Dict containing configs for each platform JSON file.
        cap_field: Capability map eg. 'ec_capability' or 'cr50_capability'.

    Returns:
        None
    """
    platform_caps = {}  # To keep track of platforms and their capabilities
    for platform, conf in consolidated.items():
        # collect explicitly defined capabilities for each platform
        caps = conf.get(cap_field, {})
        logging.debug("%s before = %s", platform, caps)
        curr_plat = platform
        while curr_plat != "DEFAULTS":
            curr_plat = consolidated[curr_plat].get("parent") or "DEFAULTS"
            parent_caps = consolidated[curr_plat].get(cap_field, {})
            for k, v in parent_caps.items():
                if k.endswith(".DOC"):
                    continue
                if k not in caps:
                    caps[k] = v
                    if v is None:
                        raise FormatException(
                            f"Capability {k} is not set",
                            platform=platform,
                            field=cap_field,
                        )
        logging.debug("%s after = %s", platform, caps)
        incl = set(k for k, v in caps.items() if v and not k.endswith(".DOC"))

        # collect the capabilities for each model
        models_caps = {}
        models = conf.get("models", {})
        for model, model_conf in models.items():
            model_caps = model_conf.get(cap_field, {})
            logging.debug("%s.%s before = %s", platform, model, model_caps)
            for k, v in caps.items():
                if k not in model_caps:
                    if k.endswith(".DOC"):
                        continue
                    model_caps[k] = v
                    if v is None:
                        raise FormatException(
                            f"Capability {k} is not set",
                            platform=platform,
                            field=cap_field,
                            model=model,
                        )
            logging.debug("%s.%s after = %s", platform, model, model_caps)
            model_incl = set(
                k for k, v in model_caps.items() if v and not k.endswith(".DOC")
            )
            models_caps[model] = model_incl

        platform_caps[platform] = incl, models_caps

    for platform, (incl, models) in platform_caps.items():
        for model, model_incl in models.items():
            consolidated[platform]["models"][model][cap_field] = sorted(
                model_incl
            )
        consolidated[platform][cap_field] = sorted(incl)


def detect_invalid_fields(consolidated):
    """Verify that all fields are present in DEFAULTS.

    Args:
        consolidated: Dict containing configs for each platform JSON file.

    Returns:
        None
    """
    for platform, conf in consolidated.items():
        if platform == "DEFAULTS":
            continue

        for field in conf:
            if field in ["models"]:
                continue
            parent = conf.get("parent", "DEFAULTS")
            if field not in consolidated["DEFAULTS"]:
                raise FormatException(
                    "Unexpected json field", platform=platform, field=field
                )
            if isinstance(consolidated["DEFAULTS"][field], dict):
                if len(conf[field]) == 0:
                    raise FormatException(
                        "Empty capabilities map",
                        platform=platform,
                        field=field,
                    )
                for subfield in conf[field]:
                    if subfield not in consolidated["DEFAULTS"][field]:
                        raise FormatException(
                            "Unexpected json field",
                            platform=platform,
                            field=f"{field}.{subfield}",
                        )
                    curr_parent = parent
                    while (
                        curr_parent
                        and consolidated[curr_parent]
                        .get(field, {})
                        .get(subfield)
                        is None
                    ):
                        curr_parent = consolidated[curr_parent].get("parent")
                    if curr_parent and conf[field][subfield] == consolidated[
                        curr_parent
                    ].get(field, {}).get(subfield):
                        raise FormatException(
                            f"Redundant setting of {field}.{subfield}:"
                            f"{conf[field][subfield]} (set in "
                            f"{curr_parent}.json)",
                            platform=platform,
                            field=f"{field}.{subfield}",
                        )
            else:
                curr_parent = parent
                while (
                    curr_parent and consolidated[curr_parent].get(field) is None
                ):
                    curr_parent = consolidated[curr_parent].get("parent")
                if curr_parent and conf[field] == consolidated[curr_parent].get(
                    field
                ):
                    raise FormatException(
                        f"Redundant setting of {field}:{conf[field]} (set in "
                        f"{curr_parent}.json)",
                        platform=platform,
                        field=field,
                    )

        models = conf.get("models", {})
        for model, model_conf in models.items():
            for field in model_conf:
                if field not in consolidated["DEFAULTS"]:
                    raise FormatException(
                        "Unexpected json field",
                        platform=platform,
                        field=field,
                        model=model,
                    )
                if isinstance(consolidated["DEFAULTS"][field], dict):
                    if len(model_conf[field]) == 0:
                        raise FormatException(
                            "Empty capabilities map",
                            platform=platform,
                            field=field,
                            model=model,
                        )
                    for subfield in model_conf[field]:
                        if subfield not in consolidated["DEFAULTS"][field]:
                            raise FormatException(
                                "Unexpected json field",
                                platform=platform,
                                field=f"{field}.{subfield}",
                                model=model,
                            )
                    curr_parent = platform
                    while (
                        curr_parent
                        and consolidated[curr_parent]
                        .get(field, {})
                        .get(subfield)
                        is None
                    ):
                        curr_parent = consolidated[curr_parent].get("parent")
                    if curr_parent and model_conf[field][
                        subfield
                    ] == consolidated[curr_parent].get(field, {}).get(subfield):
                        raise FormatException(
                            f"Redundant setting of {field}.{subfield}:"
                            f"{model_conf[field][subfield]} (set in "
                            f"{curr_parent}.json)",
                            platform=platform,
                            field=f"{field}.{subfield}",
                            model=model,
                        )
                else:
                    curr_parent = platform
                    while (
                        curr_parent
                        and consolidated[curr_parent].get(field) is None
                    ):
                        curr_parent = consolidated[curr_parent].get("parent")
                    if curr_parent and model_conf[field] == consolidated[
                        curr_parent
                    ].get(field):
                        raise FormatException(
                            f"Redundant setting of {field}:{model_conf[field]} "
                            f"(set in {curr_parent}.json)",
                            platform=platform,
                            field=field,
                            model=model,
                        )


def copy_parent_data(consolidated):
    """Copy all data from parent configs to child configs.

    Args:
        consolidated: Dict containing configs for each platform JSON file.

    Returns:
        None
    """
    for platform, conf in consolidated.items():
        if platform == "DEFAULTS":
            continue

        logging.debug("%s before = %s", platform, conf)
        curr_plat = platform
        while curr_plat != "DEFAULTS":
            curr_plat = consolidated[curr_plat].get("parent") or "DEFAULTS"
            parent_conf = consolidated[curr_plat]
            for k, v in parent_conf.items():
                if k in ["models", "parent"] or k.endswith(".DOC"):
                    continue
                if k not in conf and v is not None:
                    conf[k] = v
        logging.debug("%s after = %s", platform, conf)

        models = conf.get("models", {})
        for model, model_conf in models.items():
            logging.debug("%s.%s before = %s", platform, model, model_conf)
            for k, v in conf.items():
                if k in ["models", "parent"] or k.endswith(".DOC"):
                    continue
                if k not in model_conf and v is not None:
                    model_conf[k] = v
            logging.debug("%s.%s after = %s", platform, model, model_conf)


def write_output(consolidated_json, output_path):
    """Write consolidated JSON to a read-only file.

    Args:
        consolidated_json: Dict containing contents to write as JSON.
        output_path: The destination of the JSON.
    """
    if os.path.isfile(output_path):
        os.remove(output_path)
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(consolidated_json, output_file, indent="  ", sort_keys=True)
        output_file.write("\n")
    os.chmod(output_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def main(argv=None):
    """Load JSON from platform files, and write to output file.

    Args:
        argv: List of command-line args, excluding the invoked script.
              Typically, this should be set to sys.argv[1:].
    """
    args = parse_args(argv)
    platforms = get_platform_names(args.input_dir)
    consolidated_json = load_json(args.input_dir, platforms)
    write_output(consolidated_json, args.output)


if __name__ == "__main__":
    main(sys.argv[1:])
