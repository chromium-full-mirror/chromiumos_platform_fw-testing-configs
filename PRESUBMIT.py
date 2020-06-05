# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Presubmit checks."""

import json


def VerifyJson(input_api, output_api):
  """Verify that the json files contain valid JSON."""

  def json_file_filter(f):
    return f.LocalPath().endswith('.json')

  results = []
  for affected in input_api.AffectedFiles(
      include_deletes=False, file_filter=json_file_filter):
    name = affected.LocalPath()
    with open(name) as f:
      try:
        json.load(f)
      except Exception as e:
        err = output_api.PresubmitError(
            'Bad JSON', items=[name], long_text=str(e))
        results.append(err)

  return results


def CommonCheck(input_api, output_api):
  results = []
  results.extend(VerifyJson(input_api, output_api))
  return results


def CheckChangeOnCommit(input_api, output_api):
  results = []
  results.extend(CommonCheck(input_api, output_api))
  return results


def CheckChangeOnUpload(input_api, output_api):
  results = []
  results.extend(CommonCheck(input_api, output_api))
  return results
