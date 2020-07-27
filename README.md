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

There is one config file for each platform, named as `${PLATFORM}.json`: for example, `octopus.json`. There is also one special config file, `DEFAULTS.json`, which contains default values and documentation for each attribute. (For now, platform names are defined according to `mosys platform name`.)

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

## Accessing Configs

In Autotest, configs are loaded during `FirmwareTest.initialize`. Config values can be accessed via `self.faft_config.${ATTRIBUTE}`, such as [`self.faft_config.chrome_ec`](https://source.corp.google.com/chromeos_public/src/third_party/autotest/files/server/cros/faft/firmware_test.py;rcl=b602ca9b2516613458bccc6009ffd342130f528b;l=149).

In Tast, configs can be created via `firmware.NewConfig`. In order to conform with Go’s style, attribute names are modified to MixedCaps. Config values can be accessed via `cfg[${ATTRIBUTE}]`, such as `cfg[ChromeEC]`.

# Registering New Configs

When you create a new config for a new board, you should also register it in `tast-tests/src/chromiumos/tast/remote/firmware/config.go`'s [configPlatforms](https://source.corp.google.com/chromeos_public/src/platform/tast-tests/src/chromiumos/tast/remote/firmware/config.go;l=38). This is because datafiles used by Tast tests need to be [explicitly declared](https://chromium.googlesource.com/chromiumos/platform/tast/+/HEAD/docs/writing_tests.md#Using-data-files-in-tests). [b/162253821](https://b.corp.google.com/issues/162253821) tracks finding a way to automate that.

# Modifying Tests and Configs

Configs are now in a separate repository from Autotest or tast-tests. Thus, config edits now require a separate CL from Autotest/tast-tests edits. If you are accustomed to working with config files directly in Autotest, this is a slightly different workflow.

When you are editing config files, please be sure to run git commands from within the fw-testing-configs checkout. If you run `git add .` or `repo upload --cbr .` from within `autotest/server/cros/faft/`, then your changes to the config files will not be captured.

If you are modifying both test files and config files, then you will need at least two CL’s: one for the test change, and one for the fw-testing-configs change. Consider also whether your change will impact the other testing repositories (Autotest, Tast, SerialTest): you might need to run tests or make changes there, too.

When submitting multiple CL’s like that, please use the [Cq-Depend](https://chromium.googlesource.com/chromiumos/docs/+/refs/heads/master/contributing.md#CQ-DEPEND) syntax as appropriate. If you don't use Cq-Depend, you risk the name of a config attribute changing while tests are still looking for the old name, and then tests will break. The reverse is a risk, too. You might need both CL’s to depend on each other. Note that this while this precaution mitigates risk, it does not fully eliminate risk: only one of the CL's might get uploaded to the lab machines running Autotest/Tast, or one CL may be reverted without the other.
