CrOS fw-testing-configs: User’s Guide
=====================================

_[go/cros-fw-testing-configs-guide](https://goto.google.com/cros-fw-testing-configs-guide)_

[TOC]

# Background

End-to-end firmware testing in ChromeOS relies on board-specific configuration files. Previously, those files were stored in Autotest. Now, they have been moved into a separate repository, [fw-testing-configs](https://chromium.googlesource.com/chromiumos/platform/fw-testing-configs/), so that other testing frameworks (e.g. Tast, SerialTest) can access them too.

The design document for the new repository is at [go/cros-fw-testing-configs](https://goto.google.com/cros-fw-testing-configs).

# Working With Configs

## File Locations & Names

All the config files are located at the top directory of the fw-testing-configs repository.

The fw-testing-configs repository currently has two checkouts in the ChromeOS manifest: one inside of Autotest, and one inside of tast-tests.

There is one config file for each platform, named as `${PLATFORM}.json`: for example, `octopus.json`. There are also one special config file, `DEFAULTS.json` and `CONSOLIDATED.json`. `DEFAULTS.json` contains default values and documentation for each attribute. `CONSOLIDATED.json` is a generated file, containing the config data from all the other JSON files.

## File Contents

Each config file should contain a single object whose fields override the values specified in `DEFAULTS.json`. Any fields which do not have a corresponding value in `DEFAULTS.json` will be ignored.

There are a few special fields to be aware of:

* `platform` _(required)_: A string which should exactly match the config file’s basename (minus the `.json` extension).
* `parent` _(optional)_: A string which can contain the name of a parent platform, whose fields will be inherited with lower precedence. See “Inheritance” below. Example: [asuka.json](https://source.corp.google.com/chromeos_public/src/third_party/autotest/files/server/cros/faft/configs/asuka.json;rcl=f0ea1753123c1ef3a61d9c818b18bba5a9b574cd;l=3)
* `models` _(optional)_: An object which can contain the names of any models, whose fields will be inherited with higher precedence. See “Inheritance” below. Example: [octopus.json](https://source.corp.google.com/chromeos_public/src/third_party/autotest/files/server/cros/faft/configs/octopus.json;rcl=fe5ff0279d6b4e87311206affcb6b18d8e99a3a0;l=23)

## Inheritance

There is an inheritance model in these config files. In all cases, the most specific configuration is used:

	[Model > ] Platform [ > Parent [...] ] > DEFAULTS

For each attribute that exists in `DEFAULTS.json` (besides the documentation attributes):

* If that attribute is given a value in the platform’s `models[${MODEL}]`, then that is the value that is used.
* Otherwise, if that attribute is given a value in the `${PLATFORM}.json`, then that is the value that is used.
* Otherwise, if `${PLATFORM}.json` specifies a parent configuration via the `parent` attribute, then that is the value that is used.
* Parent configurations can specify parents as well, and the inheritance recurses until a config file does not have a `parent` attribute.
* Finally, for any attribute which was not otherwise given a value, the value from `DEFAULTS.json` is used.

# Workflows

## Consolidate before uploading

`CONSOLIDATED.json` is a generated script containing the data from all other JSON files. This allows Tast tests to access the config data. Thus, it is important to keep `CONSOLIDATED.json` up-to-date.

When you make a change to fw-testing-configs JSON, before you upload, be sure to run `./consolidate.py` (with no command-line args). This will update `CONSOLIDATED.json`. Amend your change to include the update `CONSOLIDATED.json`, and then re-upload.

A preupload hook will verify that your `CONSOLIDATED.json` is up-to-date.

## Modifying Tests and Configs

fw-testing-configs is a separate repository from both Autotest and tast-tests. Thus, edits to fw-testing-configs require a separate CL from edits to Autotest and tast-tests. If you are accustomed to working with config files directly in Autotest, this is a slightly different workflow.

When you are editing config files, please be sure to run git commands from within the fw-testing-configs checkout. If you run `git add .` or `repo upload --cbr .` from within `autotest/server/cros/faft/`, then your changes to the config files will not be captured.

If you are modifying both test files and config files, then you will need at least two CL’s: one for the test change, and one for the fw-testing-configs change. Consider also whether your change will impact the other testing repositories (Autotest, Tast, SerialTest): you might need to run tests or make changes there, too.

When submitting multiple CL’s like that, please use the [Cq-Depend](https://chromium.googlesource.com/chromiumos/docs/+/HEAD/contributing.md#CQ-DEPEND) syntax as appropriate. If you don't use Cq-Depend, you risk the name of a config attribute changing while tests are still looking for the old name, and then tests will break. The reverse is a risk, too. You might need both CL’s to depend on each other. Note that this while this precaution mitigates risk, it does not fully eliminate risk: only one of the CL's might get uploaded to the lab machines running Autotest/Tast, or one CL may be reverted without the other.

Run the unit tests inside the chroot by running
```
cd ~/chromiumos/src/platform/fw-testing-configs
pytest -v *_unittest.py
```

## Accessing Configs During Tests

In Autotest, configs are loaded during `FirmwareTest.initialize`. Config values can be accessed via `self.faft_config.${ATTRIBUTE}`, such as [`self.faft_config.chrome_ec`](https://source.corp.google.com/chromeos_public/src/third_party/autotest/files/server/cros/faft/firmware_test.py;rcl=b602ca9b2516613458bccc6009ffd342130f528b;l=149).

In Tast, configs can be created via `firmware.NewConfig`. In order to conform with Go’s style, attribute names are modified to MixedCaps. Config values can be accessed via `cfg[${ATTRIBUTE}]`, such as `cfg[ChromeEC]`.

# Utility Scripts

This repo offers a few handy-dandy utility scripts.

`consolidate.py`, as described above, combines all the individual `${PLATFORM}.json` files into one file, `CONSOLIDATED.json`:

```
> consolidate.py
```

`platform_json.py` outputs the final configuration for a single platform. `--model` or `-m` will include a model-specific override. `--field` or `-f` will only print a single field value. `--condense-output` will trim unnecessary whitespace, making it easier to consume via other scripts.

```
> platform_json.py octopus
> platform_json.py octopus -m robo360
> platform_json.py octopus -f has_lid
> platform_json.py octopus -m robo360 -f has_lid --condense-output
```

`query_by_field.py` reports a list of all platforms and models matching certain field conditions. Multiple conditions can be specified. See usage info (`query_by_field.py -h`) for details about supported operators. Note that you might need to escape some of the operators (like `\!`) for Bash to parse them.

```
> query_by_field.py has_lid=false
> query_by_field.py "firmware_screen<=8"
> query_by_field.py chrome_ec=true ec_capability\!:x86
```

Each of these scripts also supports `--help` (or `-h`) for usage info.
