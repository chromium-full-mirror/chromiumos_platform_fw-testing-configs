#!/usr/bin/env python3
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Determine which platform/model configs match a set of field conditions.

Each condition passed in as a command-line arg must be formatted as
${FIELD}${OPERATOR}${VALUE}, where:
    ${FIELD} is the name of the field being matched
    ${OPERATOR} is either '=' or '!='
    ${VALUE} is the field-value being compared against

TODO(gredelston): Add support for more operators:
    :            | array contains
    !:           | array does not contain
    <, >, <=, >= | numeric field comparisons
"""

import argparse
import re
import sys

import platform_json


RE_CONDITION = re.compile(r'^(\w+)(=|!=)(\w+)$')


class ConditionError(ValueError):
    """Error class for when a condition argument is malformed."""
    pass


class UnrecognizedOperatorError(ValueError):
    """Error class for when a query contains an unexpected operator."""


class Condition(object):
    """A condition for whether a config's field matches an expected rule."""

    def __init__(self, string_condition):
        """Parse string_condition to capture the field, operator, and value."""
        match = RE_CONDITION.match(string_condition)
        if match is None:
            raise ConditionError(string_condition)
        self.field, self.operator, self.value = match.groups()
        # All string comparisons are case-insensitive, so normalize to lower.
        self.value = self.value.lower()

    def evaluate(self, config_dict):
        """Determine whether a config dict satisfies this Condition."""
        if self.field not in config_dict:
            raise platform_json.FieldNotFoundError('%s (platform=%s)' % (
                self.field, config_dict['platform']))
        actual_value = str(config_dict[self.field]).lower()
        if self.operator == '=':
            return actual_value == self.value
        elif self.operator == '!=':
            return actual_value != self.value
        else:
            raise UnrecognizedOperatorError('%s (expect either = or !=)' %
                                            self.operator)

    def __repr__(self):
        """Represent this condition as a string."""
        return '{Condition:%s%s%s}' % (self.field, self.operator, self.value)


def parse_args(argv):
    """Parse command-line args."""
    parser = argparse.ArgumentParser()
    parser.add_argument('conditions', nargs='+',
                        help='Field-matching requirements, each of the form '
                             '${FIELD}${OPERATOR}${VALUE}, where OPERATOR is '
                             'either "=" (match) or "!=" (no match). String '
                             'comparisons are always case-insensitive.')
    parser.add_argument('-c', '--consolidated', default='CONSOLIDATED.json',
                        help='The filepath to CONSOLIDATED.json')
    args = parser.parse_args(argv)
    return args


def all_satisfied(conditions, config):
    """Determine whether the config satisfies all Conditions."""
    return all([cond.evaluate(config) for cond in conditions])


def main(argv):
    """Determine which platforms/models satisfy the passed-in conditions."""
    args = parse_args(argv)
    conditions = [Condition(str_cond) for str_cond in args.conditions]
    consolidated_json = platform_json.load_consolidated_json(args.consolidated)

    outputs = []
    for platform in consolidated_json:
        # Determine whether the platform satisfies all conditions.
        platform_config = platform_json.calculate_config(platform, None,
                                                         consolidated_json)
        platform_satisfied = all_satisfied(conditions, platform_config)

        # Check whether any of the platform's models are exceptions.
        models = consolidated_json[platform].get('models', {})
        exceptions = []
        for model in models:
            model_config = platform_json.calculate_config(platform, model,
                                                          consolidated_json)
            if all_satisfied(conditions, model_config) != platform_satisfied:
                exceptions.append(model)

        # Print if the platform or any models satisfy the conditions.
        if platform_satisfied and exceptions:
            outputs.append('%s (except %s)' % (platform, ', '.join(exceptions)))
        elif exceptions:
            outputs.append('%s (only %s)' % (platform, ', '.join(exceptions)))
        elif platform_satisfied:
            outputs.append(platform)

    if outputs:
        print('\n'.join(outputs))
    else:
        print('No platforms matched.')


if __name__ == '__main__':
    main(sys.argv[1:])
