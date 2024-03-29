# Logging warnings using the python warnings or logging module

* Status: accepted
* Date: 2022-10-18

## Context and Problem Statement

Python has two different ways to report warnings to the user. Warnings can be logged via the logger (`LOGGER.warning()`) or using the Python warnings module (`warnings.warn()`). It was unclear to developers which type of logger has to used in which circumstances.

## Decision Drivers

* By default, we don't want warnings in third-party libraries to be visible to end-users.

## Pros and Cons of each method

* LOGGER.warning():
   * This logger just writes a message to the log.
   * When the same message is logged twice, it will appear twice in the log.
* warnings.warn():
   * Each message is displayed only once.
   * Pytest provides a nice overview of all warning logged during the executing of the test suite.
   * Warnings are highly configurable through e.g. `warnings.filterwarnings`.

## Decision Outcome

- The `warnings` module will be configured as such that it ignores warnings logged from non-inmanta python modules. This way warnings from third-party libraries are ignored.
- All warnings, for which we expect an action from the end-user, should be logged using `warnings.warn()` method, and inherit from the InmantaWarning type. An example is a log message that announces a feature deprecation. This user can be a user of the CLI, the API, a module or an extension developer. Those warning won't contain the python trace.
- All other warnings should be logged using the `LOGGER.warning()` method. These warnings usually indicate that something went wong at runtime. For example, an agent that hits the rate limiter.

## Rationale

- We don't want to display python traces to end users as they contain no useful information and are clogging the logs. To prevent this we use the InmantaWarning which use a different formatting rule.
- InmantaWarning are also needed because the location the warning is about is not always the location that issues the warning. For example, when deprecated syntax is used in the inmanta model, we log a warning in core and the default warning formatter will include the line in core in the logs, while it is the line in the model that is important.
  By using InmantaWarnings, we can manually include the correct filename and line number from the model in the warning message.

## Disclaimer

At the time of writing we didn't have much experience with the different types of warnings and how they should be used.
The things mentioned above are a first attempt to add more structure to how we log warnings, but we might have to come
back on that decision later on.
