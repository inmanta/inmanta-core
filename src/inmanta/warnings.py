"""
    Copyright 2020 Inmanta

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: code@inmanta.com
"""

import logging
import warnings
from enum import Enum
from typing import Dict, List, Mapping, Optional, TextIO, Type, Union


class InmantaWarning(Warning):
    """
    Base class for Inmanta Warnings.
    """

    def __init__(self, *args: object):
        Warning.__init__(self, *args)


class WarningBehaviour(Enum):
    WARN: str = "default"
    IGNORE: str = "ignore"
    ERROR: str = "error"


class WarningRule:
    """
    A single rule for warning handling. Describes the desired behaviour when an error occurs.
    When type is set, the rule is only applied to subclasses of the warning type.
    """

    def __init__(self, action: WarningBehaviour, tp: Optional[Type[InmantaWarning]] = None) -> None:
        self.action: WarningBehaviour = action
        self.type: Type[Warning] = tp if tp is not None else InmantaWarning

    def apply(self) -> None:
        warnings.filterwarnings(self.action.value, category=self.type)


class WarningOption:
    """
    An option to manage warnings. Consists of a name and a range of possible values, each tied to a warning rule.
    For example, applying
    WarningOption(
        "disable-runtime-warnings",
        {True: WarningRule(WarningBehaviour.IGNORE, CompilerRuntimeWarning)}
    )
    would add a rule to ignore CompilerRuntimeWarnings but leave other warning's behaviour as is.
    """

    def __init__(self, name: str, options: Dict[Union[str, bool], WarningRule]) -> None:
        self.name: str = name
        self.options: Dict[Union[str, bool], WarningRule] = options

    def apply(self, option: Union[str, bool]) -> None:
        """
        Apply the warning rule tied to the given option.
        """
        if option not in self.options:
            raise Exception("Illegal option %s for %s" % (option, self.name))
        rule: WarningRule = self.options[option]
        rule.apply()


class WarningsManager:
    """
    Manages warning behaviour guided by a config file.
    """

    # List of warning options with a rule tied to each possible option value.
    # Options are applied left to right so general options should come before specific ones.
    options: List[WarningOption] = [
        WarningOption(
            "default",
            {
                "warn": WarningRule(WarningBehaviour.WARN),
                "ignore": WarningRule(WarningBehaviour.IGNORE),
                "error": WarningRule(WarningBehaviour.ERROR),
            },
        ),
    ]

    @classmethod
    def apply_config(cls, config: Optional[Mapping[str, Union[str, bool]]]) -> None:
        """
        Sets all known options based on values in config.
        """
        cls._apply_default()
        if config is None:
            return
        # apply all options, given the corresponding values in the config
        for option in cls.options:
            try:
                value: Union[str, bool] = config[option.name]
                option.apply(value)
            except KeyError:
                pass

    @classmethod
    def _apply_default(cls) -> None:
        """
        Applies the default warning behaviour.
        """
        # Control how warnings are shown
        warnings.showwarning = cls._showwarning
        # Ignore all external warnings.
        warnings.filterwarnings(WarningBehaviour.IGNORE.value, category=Warning)
        # Warn all InmantaWarnings by default. Behaviour can be controlled using the config.
        warnings.filterwarnings(WarningBehaviour.WARN.value, category=InmantaWarning)

    @classmethod
    def _showwarning(
        cls,
        message: Union[str, Warning],
        category: Type[Warning],
        filename: str,
        lineno: int,
        file: Optional[TextIO] = None,
        line: Optional[str] = None,
    ) -> None:
        """
        Shows a warning.

        :param message: The warning to show.
        :param category: The type of the warning.
        :param filename: Required for compatibility but will be ignored.
        :param lineno: Required for compatibility but will be ignored.
        :param file: The file to write the warning to. Defaults to stderr.
        :param line: Required for compatibility but will be ignored.
        """
        # implementation based on warnings._showwarnmsg_impl and logging._showwarning
        text: str
        logger: logging.Logger
        if issubclass(category, InmantaWarning):
            text = "%s: %s" % (category.__name__, message)
            logger = logging.getLogger("inmanta.warnings")
        else:
            text = warnings.formatwarning(
                # ignore type check because warnings.formatwarning accepts Warning instance but it's type definition doesn't
                message,  # type: ignore
                category,
                filename,
                lineno,
                line,
            )
            logger = logging.getLogger("py.warnings")
        if file is not None:
            try:
                # This code path is currently not used in our code base
                file.write(f"{text}\n")
            except OSError:
                pass
        else:
            logger.warning("%s", text)


def warn(warning: InmantaWarning) -> None:
    """
    Warn using the supplied InmantaWarning instance.
    """
    warnings.warn(warning)
