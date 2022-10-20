# Logging warnings using the python warnings or logging module

* Status: tentative
* Date: 2022-10-18

## Context and Problem Statement

Python has two different ways to report warnings to the user. Warnings can be logged via the logger (`LOGGER.warning()`) or using the Python warnings module (`warnings.warn()`). It was unclear to developers which type of logger has to used in which circumstances.

## Decision Drivers

* By default we don't want Deprecation warnings in third-party libraries to be visible to end-users.

## Pros and Cons of each method

* LOGGER.warning():
   * This logger just writes a message to the log.
   * When the same message is logged twice, it will appear twice in the log.
* warnings.warn():
   * Each message is displayed only once.
   * Pytest provides a nice overview of all warning logged during the executing of the test suite.
   * Warnings are highly configurable through e.g. `warnings.filterwarnings`.

## Decision Outcome

- The `warnings` module will be configured as such that all warnings not extending from the `warnings.InmantaWarning` class, are not displayed to the user. This ensures that warnings from third-party libraries are always ignored.
- All warnings logged to `warning.warn()` should extend from the `warnings.InmantaWarning` class. The `inmanta.warnings.warn()` is a wrapper around `warnigs.warn()` that ensures that this constraint is satisfied. Using the latter method is preferred.

- All warnings, for which we expect an action from the end-user, should be logged using the `inmanta.warnings.warn()` method. An example is a log message that announces a feature deprecation.
- All other warnings should be logged using the `LOGGER.warning()` method.

