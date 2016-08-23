"""
    Copyright 2016 Inmanta

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
import re
import os

from inmanta.export import export
from inmanta.ast.attribute import RelationAttribute
from inmanta.ast.entity import Entity
from inmanta.config import Config

LOGGER = logging.getLogger(__name__)


def formatMultiplicity(rel):
    low = rel.low
    high = rel.high

    if low == high:
        return low

    if high is None:
        high = "\*"

    return str(low) + ":" + str(high)


def getFirstStatement(stmts):
    out = None
    line = float("inf")
    for stmt in stmts:
        if(stmt.line > 0 and stmt.line < line):
            out = stmt
            line = stmt.line
    return out


def warn(message):
    LOGGER.warning(message)


class Emitter:
    def __init__(self, dir, file):
        self.dir = dir
        self.index = file
        contents = """Inmanta Documentation
===============================

Contents:

.. toctree::
   :maxdepth: 2

"""
        self.index.write(contents)

    def emitHeading(self, heading, char):
        """emit a sphinx heading/section  underlined by char """
        self.file.write(heading + "\n")
        self.file.write(char * len(heading) + "\n\n")

    def emitAttributes(self, entity):
        all = [entity.get_attribute(name) for name in list(entity._attributes.keys())]
        relations = [x for x in all if isinstance(x, RelationAttribute)]
        others = [x for x in all if not isinstance(x, RelationAttribute)]

        defaults = entity.get_default_values()

        if(len(others) != 0):
            self.emitHeading("attributes", "-")
        for attr in others:
            self.file.write("   .. attribute:: {2}.{0}\n\n      type: :class:`{1}`\n\n".format(
                            attr.get_name(), attr.get_type().__str__().replace("::", "."), entity.get_name()))

            if attr.get_name() in defaults:
                self.file.write("      default: {0}\n\n".format(defaults[attr.get_name()]))

        if(len(relations) != 0):
            self.emitHeading("relations", "-")

        for attr in relations:
            otherend = attr.end.get_entity().get_full_name().replace("::", ".") + "." + attr.end.get_name()
            self.file.write(("   .. attribute:: {}.{}\n\n      multiplicity: {}\n\n      reverse " +
                             "multiplicity: {}\n\n      other end: :attr:`{}`\n\n").format(
                            entity.get_name(),
                            attr.get_name(),
                            formatMultiplicity(attr),
                            formatMultiplicity(attr.end),
                            otherend))

    def emitImplementations(self, entity):
        if len(entity.implementations) != 0:
            self.emitHeading("implementations", "-")

        for impl in entity.implementations:
            self.file.write("   .. method:: {0}.{1}\n\n".format(entity.get_name(), impl.constraint))
            for impll in impl.implementations:
                first = getFirstStatement(impll.statements)
                if first:
                    self.file.write("      name: {0}  ({1}:{2}) \n\n".format(impll.name, first.filename, first.line))
                else:
                    self.file.write("      name: {0}  \n\n".format(impll.name))

    def emitEntity(self, entity):
        heading = "Entity: {0}".format(entity.get_full_name())
        self.emitHeading(heading, "=")

        self.file.write(".. class:: {0}\n\n".format(entity.get_name()))
        for x in entity.parent_entities:
            self.file.write("   superclass: :class:`{0}`\n\n".format(x.get_full_name().replace("::", ".")))
        if(entity.comment):
            self.emitComment(entity.get_full_name(), entity.comment)

        self.emitAttributes(entity)

        self.emitImplementations(entity)

        self.file.write("\n")

    def emitModule(self, module):
        entities = [var for var in module.variables() if isinstance(var.value, (Entity))]

        if len(entities) == 0:
            return

        self.index.write("   {0}\n".format(module.get_full_name().replace("::", "_")))

        with open(os.path.join(self.dir, module.get_full_name().replace("::", "_") + ".rst"), 'w') as file:
            self.file = file
            self.file.write(".. module:: {0}\n\n".format(module.get_full_name().replace("::", ".")))

            for var in entities:
                    self.emitEntity(var.value)

    def emitComment(self, context, comment):
        prewhite = re.match(r"\n?([ \t]+)", comment)
        if prewhite is not None:
            prewhite = prewhite.group(1)
            if(len(prewhite) > 0):
                comment = comment.replace(prewhite, "   ")

        if(re.search(r":param (\w+) (\w*)([^:]*)(?:$|\n)", comment)):
            warn(("DEPRECATION! :param in {0} should be of the form ':param name type: message'. " +
                  "The second ':' is missing").format(context))
            comment = re.sub(r":param (\w+) (\w*)([^:]*)($|\n)", r':param \1: \2\3\4', comment)

        # prefix with spaces
        comment = comment + "\n"

        self.file.write(comment)


@export("doc", "std::entity")
def export_doc(exporter, types):
    out_dir = Config.get("doc", "outdir", "doc")
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    with open(out_dir + '/index.rst', 'w') as file:
        em = Emitter(out_dir, file)
        root = exporter._scope
        scopes = [x for x in root.get_child_scopes() if not x.get_name().startswith("0x") and not x.get_name().startswith("__")]
        scopes = sorted(scopes, key=lambda x: x.get_full_name())
        for scope in scopes:
            em.emitModule(scope)
