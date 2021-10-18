"""
    Copyright 2018 Inmanta

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
import os
import re
from abc import abstractmethod
from typing import Any, Dict, List, Optional

from asyncpg.types import Type
from jinja2 import Environment, PackageLoader

from inmanta.ast import CompilerException, ModifiedAfterFreezeException
from inmanta.ast.statements import AssignStatement
from inmanta.ast.statements.generator import Constructor
from inmanta.execute.runtime import OptionVariable


def bold(content: Optional[str] = None) -> str:
    if content is None:
        return "\033[1m"
    return "\033[1m{0}\033[0m".format(content)


def underline(content: Optional[str] = None) -> str:
    if content is None:
        return "\033[4m"
    return "\033[4m{0}\033[0m".format(content)


def noformat(content: Optional[str] = None) -> str:
    return "\033[0m"


CUSTOM_FILTERS = {"bold": bold, "underline": underline, "noformat": noformat}


class Explainer(object):
    @abstractmethod
    def explain(self, problem: CompilerException) -> List[str]:
        pass


class JinjaExplainer(Explainer):
    def __init__(self, template: str, acceptable_type: Type) -> None:
        self.template = template
        self.acceptable_type = acceptable_type

    def can_handle(self, problem: CompilerException) -> bool:
        return isinstance(problem, self.acceptable_type)

    def get_template(self, problem: CompilerException) -> str:
        path = os.path.join(os.path.dirname(__file__), self.template)
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()

    def explain(self, problem: CompilerException) -> List[str]:
        allcauses = set()
        work = [problem]
        while work:
            w = work.pop()
            allcauses.add(w)
            work.extend(w.get_causes())

        explainable = [c for c in allcauses if self.can_handle(c)]

        if not explainable:
            return []
        else:
            return [self.do_explain(x) for x in explainable]

    def do_explain(self, problem: CompilerException) -> str:
        env = Environment(loader=PackageLoader("inmanta.compiler.help"))
        for name, filter in CUSTOM_FILTERS.items():
            env.filters[name] = filter

        template = env.get_template(self.template)
        return template.render(**self.get_arguments(problem))

    def get_arguments(self, problem: CompilerException) -> Dict[str, Any]:
        return {}


class ModifiedAfterFreezeExplainer(JinjaExplainer):
    def __init__(self) -> None:
        super(ModifiedAfterFreezeExplainer, self).__init__("modified_after_freeze.j2", ModifiedAfterFreezeException)

    def build_reverse_hint(self, problem: CompilerException) -> str:
        if isinstance(problem.stmt, AssignStatement):
            return "%s.%s = %s" % (
                problem.stmt.rhs.pretty_print(),
                problem.attribute.get_name(),
                problem.stmt.lhs.pretty_print(),
            )

        if isinstance(problem.stmt, Constructor):
            # find right parameter:
            attr = problem.attribute.end.get_name()
            if attr not in problem.stmt.get_attributes():
                attr_rhs = "?"
            else:
                attr_rhs = problem.stmt.get_attributes()[attr].pretty_print()
            return "%s.%s = %s" % (attr_rhs, problem.attribute.get_name(), problem.stmt.pretty_print())

    def get_arguments(self, problem: CompilerException) -> Dict[str, Any]:
        return {
            "relation": problem.attribute.get_name(),
            "instance": problem.instance,
            "values": problem.resultvariable.value,
            "value": problem.value,
            "location": problem.location,
            "reverse": problem.reverse,
            "reverse_example": "" if not problem.reverse else self.build_reverse_hint(problem),
            "optional": isinstance(problem.resultvariable, OptionVariable),
        }


def escape_ansi(line: str) -> str:
    ansi_escape = re.compile(r"(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", line)


class ExplainerFactory(object):
    def get_explainers(self) -> List[Explainer]:
        return [ModifiedAfterFreezeExplainer()]

    def explain(self, problem: CompilerException) -> List[str]:
        return [explanation for explainer in self.get_explainers() for explanation in explainer.explain(problem)]

    def explain_and_format(self, problem: CompilerException, plain: bool = True) -> Optional[str]:
        """
        :param plain: remove tty color codes, only return plain text
        """
        raw = self.explain(problem)
        if not raw:
            return None
        else:
            pre = """
\033[1mException explanation
=====================\033[0m
"""
            pre += "\n\n".join(raw)

            if not plain:
                return pre
            else:
                return escape_ansi(pre)
