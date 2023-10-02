# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Presubmit checks."""

import json


USE_PYTHON3 = True


def VerifyJson(input_api, output_api):
    """Verify that the json files contain valid JSON."""

    def json_file_filter(f):
        return f.LocalPath().endswith(".json")

    results = []
    for affected in input_api.AffectedFiles(
        include_deletes=False, file_filter=json_file_filter
    ):
        name = affected.LocalPath()
        with open(name, encoding="utf-8") as f:
            try:
                json.load(f)
            except Exception as e:
                err = output_api.PresubmitError(
                    "Bad JSON", items=[name], long_text=str(e)
                )
                results.append(err)

    return results


def VerifyConsolidated(input_api, output_api):
    """Verify that re-running consolidate.py creates no diff."""
    results = []
    script_basename = "consolidate.py"
    script_fullpath = input_api.os_path.join(
        input_api.PresubmitLocalPath(), script_basename
    )
    json_basename = "CONSOLIDATED.json"
    json_fullpath = input_api.os_path.join(
        input_api.PresubmitLocalPath(), json_basename
    )
    tmp_json = input_api.os_path.join("/tmp", json_basename)
    if not input_api.os_path.isfile(json_fullpath):
        msg = "Error: %s not found. Please run %s and try again." % (
            json_basename,
            script_basename,
        )
        results.append(output_api.PresubmitError(msg))
    elif input_api.subprocess.call(
        [script_fullpath, "-o", tmp_json],
        stdout=input_api.subprocess.PIPE,
        stderr=input_api.subprocess.PIPE,
    ):
        msg = "Error: %s failed. Please fix and try again." % script_basename
        results.append(output_api.PresubmitError(msg))
    elif not input_api.os_path.isfile(tmp_json):
        msg = "Error: %s did not produce output. Please fix and try again." % (
            script_basename
        )
        results.append(output_api.PresubmitError(msg))
    elif input_api.subprocess.call(
        ["diff", json_fullpath, tmp_json],
        stdout=input_api.subprocess.PIPE,
        stderr=input_api.subprocess.PIPE,
    ):
        msg = (
            "Error: Running %s produced a diff. Please run the script, "
            "amend your changes, and try again."
        ) % script_basename
        results.append(output_api.PresubmitError(msg))
    elif input_api.subprocess.call(
        ["git", "diff", "--exit-code", json_fullpath],
        stdout=input_api.subprocess.PIPE,
        stderr=input_api.subprocess.PIPE,
    ):
        msg = (
            "Error: %s has unstaged changes. Please amend your commit and "
            "try again."
        ) % json_fullpath
        results.append(output_api.PresubmitError(msg))
    elif input_api.subprocess.call(
        ["git", "diff", "--exit-code", "--staged", json_fullpath],
        stdout=input_api.subprocess.PIPE,
        stderr=input_api.subprocess.PIPE,
    ):
        msg = (
            "Error: %s has uncommitted changes. Please commit your staged "
            "changes and try again."
        ) % json_fullpath
        results.append(output_api.PresubmitError(msg))
    if input_api.os_path.isfile(tmp_json):
        input_api.subprocess.call(
            ["rm", "-f", tmp_json],
            stdout=input_api.subprocess.PIPE,
            stderr=input_api.subprocess.PIPE,
        )
    return results


def CommonCheck(input_api, output_api):
    results = []
    results.extend(VerifyJson(input_api, output_api))
    results.extend(VerifyConsolidated(input_api, output_api))
    # Tests don't normally cause repo upload to fail, and the "warnings"
    # that it emits are hidden. Setting no_diffs tricks the tests into failing
    # instead of warning.
    save = input_api.no_diffs
    try:
        input_api.no_diffs = True
        tests = input_api.canned_checks.GetUnitTestsInDirectory(
            input_api,
            output_api,
            input_api.PresubmitLocalPath(),
            files_to_check=[r".+_unittest\.py$"],
        )
        results.extend(input_api.RunTests(tests))
    finally:
        input_api.no_diffs = save
    return results


def CheckChangeOnCommit(input_api, output_api):
    results = []
    results.extend(CommonCheck(input_api, output_api))
    return results


def CheckChangeOnUpload(input_api, output_api):
    results = []
    results.extend(CommonCheck(input_api, output_api))
    return results
