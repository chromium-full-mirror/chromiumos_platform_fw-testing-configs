#!/usr/bin/env python3
# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Compares the configuration in chromite.lib.firmware.ap_firmware_config
to the config in consolidated.json and verifies that the ap_flash over ccd
commands match.
"""

import argparse
import glob
import importlib
import logging
import os
import sys

from chromite.lib.firmware import ap_firmware_config, servo_lib

import platform_json

CONFIG_FILE_PATTERN = os.path.join(
    os.path.dirname(ap_firmware_config.__file__), '[!_]*.py')


class _ServoStatus:
    """Mock object for ap_firmware_config.

    We only support ccd.
    """
    is_ccd = True
    is_c2d2 = False
    is_micro = False
    is_v2 = False
    is_v4 = False
    version = 'fake_servo'
    serial = '%s'


def parse_args(argv):
    """Parse command-line args."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--consolidated', default='CONSOLIDATED.json',
                        help='The filepath to CONSOLIDATED.json')
    args = parser.parse_args(argv)
    return args


def _compare_lists(ap_list, json_list):
    """Compare the list of dut-control commands from ap_firmware_config and
    consolidated.json."""
    if len(ap_list) != len(json_list):
        return False
    i = 0
    while i < len(ap_list):
        ap_val = ap_list[i][0]
        json_val = json_list[i]
        if ap_val != json_val:
            return False
        i += 1
    return True


def main(argv):
    logging.basicConfig(level=logging.INFO)
    args = parse_args(argv)
    consolidated_json = platform_json.load_consolidated_json(args.consolidated)

    servo_status = _ServoStatus()
    for f in glob.glob(CONFIG_FILE_PATTERN):
        board = os.path.splitext(os.path.basename(f))[0]
        ap_fw_config = importlib.import_module(
            f'chromite.lib.firmware.ap_firmware_config.{board}')
        ap_config = None
        platform_config = None
        try:
            ap_config = ap_fw_config.get_config(servo_status)
        except servo_lib.UnsupportedServoVersionError:
            pass
        try:
            platform_config = platform_json.calculate_config(board, None,
                                                             consolidated_json)
        except platform_json.PlatformNotFoundError:
            pass

        if platform_config:
            if ap_config:
                if (ap_config.programmer !=
                        platform_config['ap_flash_ccd_programmer']):
                    raise Exception(
                        '%s: ap_flash_ccd_programmer "%s" != "%s"' % (
                            board, platform_config['ap_flash_ccd_programmer'],
                            ap_config.programmer))
                if not _compare_lists(
                    ap_config.dut_control_on,
                        platform_config['ap_flash_ccd_pre_commands']):
                    raise Exception(
                        '%s: ap_flash_ccd_pre_commands "%s" != "%s"' %
                        (board, platform_config['ap_flash_ccd_pre_commands'],
                         ap_config.dut_control_on))
                if not _compare_lists(
                    ap_config.dut_control_off,
                        platform_config['ap_flash_ccd_post_commands']):
                    raise Exception(
                        '%s: ap_flash_ccd_post_commands "%s" != "%s"' %
                        (board, platform_config['ap_flash_ccd_post_commands'],
                         ap_config.dut_control_off))
            elif platform_config['ap_flash_ccd_programmer']:
                raise Exception('%s: ap_flash_ccd_programmer != null' % board)
        else:
            logging.debug('Skipping %s, no JSON config.', board)


if __name__ == '__main__':
    main(sys.argv[1:])
