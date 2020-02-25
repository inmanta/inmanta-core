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

import warnings
from configparser import SectionProxy
from typing import Dict, List, Optional, Type, Union


class WarningRule:
    """
        A single rule for warning handling.
    """

    def __init__(
        self,
        action: str,
        message: Optional[str] = None,
        category: Optional[Type[Warning]] = None,
        module: Optional[str] = None,
        line: Optional[int] = None,
    ) -> None:
        self.action: str = action
        self.message: Optional[str] = message
        self.category: Optional[Type[Warning]] = category
        self.module: Optional[str] = module
        self.line: Optional[int] = line

    def apply(self) -> None:
        kwargs = dict(filter(lambda x: x[1] is not None, vars(self).items()))
        warnings.filterwarnings(**kwargs)


class WarningOption:
    """
        An option to manage warnings.
    """

    def __init__(self, name: str, options: Dict[Union[str, bool], WarningRule], default: Optional[WarningRule] = None,) -> None:
        self.name: str = name
        self.options: Dict[Union[str, bool], WarningRule] = options
        self.default: Optional[WarningRule] = default

    def apply(self, option: Union[str, bool]) -> None:
        if option not in self.options:
            if self.default is None:
                raise Exception("Illegal option %s for %s" % (option, self.name))
            self.default.apply()
        rule: WarningRule = self.options[option]
        rule.apply()


class WarningsManager:
    """
        Contains all WarningOptions.
    """

    options: List[WarningOption] = [
        WarningOption(
            "default", {"warn": WarningRule("default"), "ignore": WarningRule("ignore"), "error": WarningRule("error")}
        ),
    ]

    @classmethod
    def apply_config(cls, config: Optional[SectionProxy]) -> None:
        if config is None:
            return
        for option in cls.options:
            try:
                value: Union[str, bool] = config[option.name]
                option.apply(value)
            except KeyError:
                pass


class InmantaWarning(Warning):
    """
        Base class for Inmanta Warnings.
    """

    def __init__(self):
        Warning.__init__(self)
