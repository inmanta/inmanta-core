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
from abc import ABC, abstractmethod
from typing import Generic, List, Mapping, Optional, Sequence, Set, Type, TypeVar

from jinja2 import Environment, PackageLoader

from inmanta.ast import CompilerException, ModifiedAfterFreezeException
from inmanta.ast.statements import AssignStatement
from inmanta.ast.statements.generator import Constructor, IndexCollisionException
from inmanta.execute.runtime import OptionVariable
from inmanta.module import ModuleV2InV1PathException


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


class ExplainerABC(ABC):
    """
    Abstract base class for explainers. This class is purposely kept non-Generic to present a public interface that is invariant
    of the compiler exception type. This allows correct typing of sequences of explainers.
    """

    @abstractmethod
    def explain(self, problem: CompilerException) -> List[str]:
        ...


Explainable = TypeVar("Explainable", bound=CompilerException)


class Explainer(Generic[Explainable], ExplainerABC, ABC):
    """
    Abstract explainer, Generic in the compiler exception subtype to allow correct typing of the exception for subtype-specific
    explanation logic.
    Concrete subclasses must not be generic in the exception type because this would break explainable checking.
    """

    explainable_type: Type[Explainable]

    def explain(self, problem: CompilerException) -> List[str]:
        """
        Returns a list of explanations for this exception. If neither the exception or any of its causes (recursively)
        is explainable by this explainer, returns an empty list.
        """
        allcauses: Set[CompilerException] = set()
        work: List[CompilerException] = [problem]
        while work:
            w = work.pop()
            allcauses.add(w)
            work.extend(w.get_causes())

        return [self.do_explain(c) for c in allcauses if isinstance(c, self.explainable_type)]

    @abstractmethod
    def do_explain(self, problem: Explainable) -> str:
        """
        Explain a single exception, explainable by this explainer. Does not recurse on its causes.
        """
        ...


class JinjaExplainer(Explainer[Explainable], ABC):
    """
    Abstract explainer for explanations based on a Jinja template.

    :param template: path to the Jinja template to use for the explanation.
    """

    def __init__(self, template: str) -> None:
        self.template: str = template

    def get_template(self, problem: Explainable) -> str:
        path = os.path.join(os.path.dirname(__file__), self.template)
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()

    def do_explain(self, problem: Explainable) -> str:
        env = Environment(loader=PackageLoader("inmanta.compiler.help"))
        for name, filter in CUSTOM_FILTERS.items():
            env.filters[name] = filter

        template = env.get_template(self.template)
        return template.render(**self.get_arguments(problem))

    @abstractmethod
    def get_arguments(self, problem: Explainable) -> Mapping[str, object]:
        """
        Returns a mapping for names that are used in the Jinja template.
        """
        ...


class ModifiedAfterFreezeExplainer(JinjaExplainer[ModifiedAfterFreezeException]):
    """
    Explainer for ModifiedAfterFreezeException.
    """

    explainable_type: Type[ModifiedAfterFreezeException] = ModifiedAfterFreezeException

    def __init__(self) -> None:
        super().__init__("modified_after_freeze.j2")

    def build_reverse_hint(self, problem: ModifiedAfterFreezeException) -> str:
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

    def get_arguments(self, problem: ModifiedAfterFreezeException) -> Mapping[str, object]:
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


class ModuleV2InV1PathExplainer(JinjaExplainer[ModuleV2InV1PathException]):
    """
    Explainer for ModuleV2InV1PathException
    """

    explainable_type: Type[ModuleV2InV1PathException] = ModuleV2InV1PathException

    def __init__(self) -> None:
        super().__init__("module_v2_in_v1_path.j2")

    def get_arguments(self, problem: ModuleV2InV1PathException) -> Mapping[str, object]:
        v2_source_configured: bool = problem.project.module_v2_source_configured() if problem.project is not None else False
        return {
            "name": problem.module.name,
            "path": problem.module.path,
            "project": problem.project is not None,
            "v2_source_configured": v2_source_configured,
        }


class IndexCollisionExplainer(JinjaExplainer[IndexCollisionException]):
    """
    Explainer for IndexCollisionException
    """

    explainable_type: Type[IndexCollisionException] = IndexCollisionException

    def __init__(self) -> None:
        super().__init__("index_collision.j2")

    def get_arguments(self, problem: IndexCollisionException) -> Mapping[str, object]:
        return {
            "constructor_str": problem.constructor.pretty_print(),
            "constructor_loc": problem.constructor.location,
            "constructor_name": problem.constructor.class_type,
            "collisions": {",".join(index): instance for index, instance in problem.collisions.items()},
        }


def escape_ansi(line: str) -> str:
    ansi_escape = re.compile(r"(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", line)


class ExplainerFactory:
    def get_explainers(self) -> Sequence[ExplainerABC]:
        return [ModifiedAfterFreezeExplainer(), ModuleV2InV1PathExplainer(), IndexCollisionExplainer()]

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
