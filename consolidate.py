#!/usr/bin/env python3
# Copyright 2020 The Chromium OS Authors. All rights reserved.
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
import os
import stat
import sys


DEFAULT_OUTPUT_FILEPATH = 'CONSOLIDATED.json'


class FormatException(Exception):
    def __init__(self, message, platform=None, field=None):
        if not message:
            message = 'Formatting issue in platform json'
        if platform:
            message += ', in platform {}'.format(platform)
        if field:
            message += ', in field {}'.format(field)
        message += '!'
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
    parser.add_argument('-i', '--input-dir',
                        help='Directory with fw-testing-configs JSON files',
                        default=os.path.dirname(__file__))
    parser.add_argument('-o', '--output', help='Filepath to write output to',
                        default=DEFAULT_OUTPUT_FILEPATH)
    return parser.parse_args(argv)


def get_platform_names(fwtc_dir):
    """Create a list of platforms with JSON files.

    Args:
        fwtc_dir: The fw-testing-configs directory containing platform JSON files.

    Returns:
        A list of strings representing the names of platforms which have JSON
        files in fwtc_dir, starting with DEFAULTS and then alphabetically.
        These names do not include .json.
    """
    platforms = []
    for fname in os.listdir(fwtc_dir):
        platform, ext = os.path.splitext(fname)
        if ext != '.json':
            continue
        elif platform in ('DEFAULTS', 'CONSOLIDATED'):
            continue
        platforms.append(platform)
    platforms.sort()
    platforms = ['DEFAULTS'] + platforms
    return platforms


def load_json(fwtc_dir, platforms):
    """Create an OrderedDict of {platform_name: json_contents}.

    Args:
        fwtc_dir: The fw-testing-configs directory containing platform JSON files.
        platforms: A sorted list of names which have JSON files in fwtc_dir.

    Returns:
        An OrderedDict whose keys are platforms in the same order as in the
        passed-in param, and whose values OrderedDicts representing the contents
        of that platform's corresponding ${PLATFORM}.json file.
    """
    consolidated = collections.OrderedDict()
    for platform in platforms:
        json_path = os.path.join(fwtc_dir, platform + '.json')
        with open(json_path) as json_file:
            j = json.load(json_file, object_pairs_hook=collections.OrderedDict)
        consolidated[platform] = j
    reformat_capability_map(consolidated, 'ec_capability')
    reformat_capability_map(consolidated, 'cr50_capability')
    return consolidated


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
    platform_caps = dict()  # To keep track of platforms and their capabilities
    # To keep track of all capabilities expected to be defined
    full_cap_set = set()
    for platform, conf in consolidated.items():
        if platform == 'DEFAULTS':
            # Collect set of all possible settings
            full_cap_set = set(conf.get(cap_field, dict()).keys())

        # collect explicitly defined capabilities for each platform
        caps = conf.get(cap_field, dict())
        incl = set(k for k, v in caps.items() if v)
        excl = set(k for k, v in caps.items() if not v and v is not None)
        platform_caps[platform] = incl, excl

    # For platforms with explicitly defined capabilities, recurse through parents
    # inheritance from parents is overridden by children
    # Need separate loop to ensure incl, excl calculated for parent platforms
    for platform, (incl, excl) in platform_caps.items():
        curr_plat = platform
        seen = {platform}
        while True:
            curr_plat = consolidated[curr_plat].get('parent') or 'DEFAULTS'

            # Check that there is no cycle of inheritance
            if curr_plat not in seen:
                seen.add(curr_plat)
            elif curr_plat == 'DEFAULTS':
                break
            else:
                raise FormatException(
                    'Circular parent from platform json',
                    platform=platform, field='parent')

            par_incl, par_excl = platform_caps.get(curr_plat, (set(), set()))
            # ensure children get precedence in inheriting capabilities
            incl = incl.union(par_incl.difference(excl))
            excl = excl.union(par_excl.difference(incl))

        if platform != 'DEFAULTS':
            # Raise error if capability undefined after inheriting from parents
            if incl.union(excl) != full_cap_set:
                raise FormatException(
                    'Not all capabilities accounted for',
                    platform=platform, field=cap_field)
            # Raise error if capability is somehow both defined true and false
            if incl.intersection(excl):
                raise FormatException(
                    'Include/exclude not mutually exclusive',
                    platform=platform, field=cap_field)

        consolidated[platform][cap_field] = sorted(incl)


def write_output(consolidated_json, output_path):
    """Write consolidated JSON to a read-only file.

    Args:
        consolidated_json: Dict containing contents to write as JSON.
        output_path: The destination of the JSON.
    """
    if os.path.isfile(output_path):
        os.remove(output_path)
    with open(output_path, 'w') as output_file:
        json.dump(consolidated_json, output_file, indent='\t')
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


if __name__ == '__main__':
    main(sys.argv[1:])
