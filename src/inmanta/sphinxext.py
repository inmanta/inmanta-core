# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# based on oslo_config.sphinxext
# http://docs.openstack.org/developer/oslo.config/sphinxext.html

from collections import defaultdict
import importlib
import os
import re
import shutil
import sys
import tempfile

from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain
from sphinx.domains import ObjType
from sphinx.locale import l_
from sphinx.roles import XRefRole
from sphinx.util import docstrings
from sphinx.util.nodes import make_refnode
from sphinx.util.nodes import nested_parse_with_titles

from inmanta import module, compiler
from inmanta.ast.attribute import RelationAttribute
from inmanta.config import Config
from inmanta.module import Project
from inmanta.plugins import PluginMeta


def _indent(text, n=2):
    padding = ' ' * n
    return '\n'.join(padding + l for l in text.splitlines())


def _make_anchor_target(group_name, option_name):
    # We need to ensure this is unique across entire documentation
    # http://www.sphinx-doc.org/en/stable/markup/inline.html#ref-role
    target = '%s.%s' % (group_name,
                        option_name.lower())
    return target


def _format_group(app, group_name, opt_list):
    group_name = group_name or 'DEFAULT'
    app.info('[inmanta.config] %s' % (group_name))

    yield '.. inmanta.config:group:: %s' % group_name
    yield ''

    for opt in sorted(opt_list.values(), key=lambda x: x.name):
        yield '.. inmanta.config:option:: %s' % opt.name
        yield ''

        typ = opt.get_type()
        if typ:
            yield _indent(':Type: %s' % typ)
        default = opt.get_default_desc()
        if default:
            default = '``' + str(default).strip() + '``'
            yield _indent(':Default: %s' % default)
#         if getattr(opt.type, 'min', None) is not None:
#             yield _indent(':Minimum Value: %s' % opt.type.min)
#         if getattr(opt.type, 'max', None) is not None:
#             yield _indent(':Maximum Value: %s' % opt.type.max)
#         if getattr(opt.type, 'choices', None):
#             choices_text = ', '.join([_get_choice_text(choice)
#                                       for choice in opt.type.choices])
#             yield _indent(':Valid Values: %s' % choices_text)

        yield ''

        try:
            help_text = opt.documentation % {'default': 'the value above'}
        except (TypeError, KeyError):
            # There is no mention of the default in the help string,
            # or the string had some unknown key
            help_text = opt.documentation
        if help_text:
            yield _indent(help_text)
            yield ''

#         if opt.deprecated_opts:
#             for line in _list_table(
#                     ['Group', 'Name'],
#                     ((d.group or 'DEFAULT',
#                       d.name or opt.dest or 'UNSET')
#                      for d in opt.deprecated_opts),
#                     title='Deprecated Variations'):
#                 yield _indent(line)
#         if opt.deprecated_for_removal:
#             yield _indent('.. warning::')
#             yield _indent('   This option is deprecated for removal.')
#             yield _indent('   Its value may be silently ignored ')
#             yield _indent('   in the future.')
#             yield ''
#             if opt.deprecated_reason:
#                 yield _indent('   :Reason: ' + opt.deprecated_reason)
#             yield ''

        yield ''


class ConfigOptXRefRole(XRefRole):
    "Handles :inmanta.config:option: roles pointing to configuration options."

    def __init__(self):
        super(ConfigOptXRefRole, self).__init__(warn_dangling=True)

    def process_link(self, env, refnode, has_explicit_title, title, target):
        if not has_explicit_title:
            title = target
        if '.' in target:
            group, opt_name = target.split('.')
        else:
            group = 'DEFAULT'
            opt_name = target
        anchor = _make_anchor_target(group, opt_name)
        return title, anchor


class ConfigGroup(rst.Directive):

    has_content = True

    option_spec = {
        'namespace': directives.unchanged,
    }

    def run(self):
        env = self.state.document.settings.env
        app = env.app

        group_name = ' '.join(self.content)

        cached_groups = env.domaindata['inmanta.config']['groups']

        # Store the current group for use later in option directives
        env.temp_data['inmanta.config:group'] = group_name
        app.info('inmanta.config group %r' % group_name)

        # Store the location where this group is being defined
        # for use when resolving cross-references later.
        # FIXME: This should take the source namespace into account, too
        cached_groups[group_name] = env.docname

        result = ViewList()
        source_name = '<' + __name__ + '>'

        def _add(text):
            "Append some text to the output result view to be parsed."
            result.append(text, source_name)

        title = group_name

        _add(title)
        _add('-' * len(title))
        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, result, node)

        first_child = node.children[0]

        # Compute the normalized target and set the node to have that
        # as an id
        target_name = group_name
        first_child['ids'].append(target_name)

        indexnode = addnodes.index(entries=[])
        return [indexnode] + node.children


class ConfigOption(ObjectDescription):
    "Description of a configuration option (.. option)."
    def handle_signature(self, sig, signode):
        """Transform an option description into RST nodes."""
        optname = sig
        self.env.app.info('inmanta.config option %s' % optname)
        # Insert a node into the output showing the option name
        signode += addnodes.desc_name(optname, optname)
        signode['allnames'] = [optname]
        return optname

    def add_target_and_index(self, firstname, sig, signode):
        cached_options = self.env.domaindata['inmanta.config']['options']
        # Look up the current group name from the processing context
        currgroup = self.env.temp_data.get('inmanta.config:group')
        # Compute the normalized target name for the option and give
        # that to the node as an id
        target_name = _make_anchor_target(currgroup, sig)
        signode['ids'].append(target_name)
        self.state.document.note_explicit_target(signode)
        # Store the location of the option definition for later use in
        # resolving cross-references
        # FIXME: This should take the source namespace into account, too
        cached_options[target_name] = self.env.docname


class ConfigGroupXRefRole(XRefRole):
    "Handles :inmanta.config:group: roles pointing to configuration groups."

    def __init__(self):
        super(ConfigGroupXRefRole, self).__init__(warn_dangling=True)

    def process_link(self, env, refnode, has_explicit_title, title, target):
        # The anchor for the group link is the group name.
        return target, target


def _format_option_help(app):
    """Generate a series of lines of restructuredtext.

    Format the option help as restructuredtext and return it as a list
    of lines.
    """

    opts = Config.get_config_options()

    for section, opt_list in sorted(opts.items(), key=lambda x: x[0]):
        lines = _format_group(
            app=app,
            group_name=section,
            opt_list=opt_list
        )
        for line in lines:
            yield line


def format_multiplicity(rel):
    low = rel.low
    high = rel.high

    if low == high:
        return low

    if high is None:
        high = "\*"

    return str(low) + ":" + str(high)


def get_first_statement(stmts):
    out = None
    line = float("inf")
    for stmt in stmts:
        if(stmt.line > 0 and stmt.line < line):
            out = stmt
            line = stmt.line
    return out


ATTRIBUTE_REGEX = re.compile("(?::param|:attribute|:attr) (.*?)(?:(?=:param)|(?=:attribute)|(?=:attr)|\Z)", re.S)
ATTRIBUTE_LINE_REGEX = re.compile("([^\s:]+)(:)?\s(.*?)\Z")
PARAM_REGEX = re.compile(":param|:attribute|:attr")


def parse_docstring(docstring):
    """
        Parse a docstring and return its components. Inspired by
        https://github.com/openstack/rally/blob/master/rally/common/plugin/info.py#L31-L79

        :param str docstring: The string/comment to parse in docstring elements
        :returns: {
            "comment": ...,
            "attributes": ...,
        }
    """
    docstring = "\n".join(docstrings.prepare_docstring(docstring))

    comment = docstring
    attributes = {}
    match = PARAM_REGEX.search(docstring)
    if match:
        comment = docstring[:match.start()]

        # process params
        attr_lines = ATTRIBUTE_REGEX.findall(docstring)
        for line in attr_lines:
            line = re.sub("\s+", " ", line.strip())
            match = ATTRIBUTE_LINE_REGEX.search(line)
            if match is None:
                print("Unable to parse line: " + line, file=sys.stderr)

            items = match.groups()
            attributes[items[0]] = items[2]

    comment_lines = []
    for line in comment.split("\n"):
        line = line.strip()
        if len(line) > 0:
            comment_lines.append(line)

    return {"comment": comment_lines, "attributes": attributes}


class ShowOptionsDirective(rst.Directive):

    option_spec = {
        'split-namespaces': directives.flag,
        'config-file': directives.unchanged,
    }

    has_content = True

    def run(self):
        env = self.state.document.settings.env
        app = env.app

        namespaces = [c.strip() for c in self.content if c.strip()]
        for namespace in namespaces:
            importlib.import_module(namespace)

        result = ViewList()
        source_name = '<' + __name__ + '>'
        for line in _format_option_help(app):
            result.append(line, source_name)

        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, result, node)

        return node.children


def module_list(argument):
    if argument is None:
        return []
    return [x.strip() for x in argument.split(",")]


class ShowModule(rst.Directive):
    has_content = True

    option_spec = {
        'additional_modules': module_list,
    }

    def doc_compile(self, module_dir, name, import_list):
        curdir = os.getcwd()
        main_cf = "\n".join(["import " + i for i in import_list])
        try:
            project_dir = tempfile.mkdtemp()
            with open(os.path.join(project_dir, "main.cf"), "w+") as fd:
                fd.write(main_cf)

            with open(os.path.join(project_dir, "project.yml"), "w+") as fd:
                fd.write("""name: docgen
description: Project to generate docs
repo: %s
modulepath: %s
    """ % (module_dir, module_dir))

            project = Project(project_dir)
            project.use_virtual_env()
            Project.set(project)
            project.verify()
            project.load()
            values = compiler.do_compile()

            lines = []
            modules = defaultdict(dict)
            for type_name, type_obj in values[0].items():
                if hasattr(type_obj, "comment"):
                    module = type_name.split("::")[:-1]
                    modules["::".join(module)][type_name] = type_obj

            lines.extend(self.emit_heading("Entities", "-"))
            for module in sorted(modules.keys()):
                if module[:len(name)] == name:
                    for type_name in sorted(modules[module].keys()):
                        lines.extend(self.emit_entity(modules[module][type_name]))

            plugins = {plugin: obj for plugin, obj in PluginMeta.get_functions().items() if plugin[:len(name)] == name}
            lines.extend(self.emit_heading("Plugins", "-"))
            for plugin in sorted(plugins.keys()):
                cls = plugins[plugin]
                lines.extend(self.emit_plugin(plugin, cls))

            return lines
        finally:
            os.chdir(curdir)
            shutil.rmtree(project_dir)

        return []

    def emit_plugin(self, name, cls):
        instance = cls(None)
        lines = [".. py:function:: " + instance.get_signature(), ""]
        if cls.__function__.__doc__ is not None:
            docstring = ["   " + x for x in docstrings.prepare_docstring(cls.__function__.__doc__)]
            lines.extend(docstring)
            lines.append("")
        return lines

    def emit_heading(self, heading, char):
        """emit a sphinx heading/section  underlined by char """
        return [heading, char * len(heading), ""]

    def emit_attributes(self, entity, attributes):
        all_attributes = [entity.get_attribute(name) for name in list(entity._attributes.keys())]
        relations = [x for x in all_attributes if isinstance(x, RelationAttribute)]
        others = [x for x in all_attributes if not isinstance(x, RelationAttribute)]

        defaults = entity.get_default_values()
        lines = []

        for attr in others:
            name = attr.get_name()

            attr_line = "   .. inmanta:attribute:: {1} {2}.{0}".format(attr.get_name(), attr.get_type().__str__(),
                                                                       entity.get_full_name())
            if attr.get_name() in defaults:
                attr_line += "=" + str(defaults[attr.get_name()])
            lines.append(attr_line)
            lines.append("")
            if name in attributes:
                lines.append("      " + attributes[name])

            lines.append("")

        for attr in relations:
            lines.append("   .. inmanta:relation:: {} {}.{} [{}]".format(attr.get_type(), entity.get_full_name(),
                                                                         attr.get_name(), format_multiplicity(attr)))
            lines.append("")
            if attr.end is not None:
                otherend = attr.end.get_entity().get_full_name() + "." + attr.end.get_name()
                lines.append("      other end: :inmanta:relation:`{0} [{1}]<{0}>`".format(otherend,
                                                                                          format_multiplicity(attr.end)))
                lines.append("")

        return lines

    def emit_implementations(self, entity):
        lines = []
        for impl in entity.implementations:
            lines.append("   .. inmanta:implementation:: {0}.{1}".format(entity.get_full_name(), impl.name))
            lines.append("")
#             for impll in impl.implementations:
#                 first = get_first_statement(impll.statements)
#                 if first:
#                     lines.append("      name: {0}  ({1}:{2}) \n\n".format(impll.name, first.filename, first.line))
#                 else:
#                     lines.append("      name: {0}  \n\n".format(impll.name))

        return lines

    def emit_entity(self, entity):
        lines = []
        lines.append(".. inmanta:entity:: " + entity.get_full_name())
        lines.append("")

        if len(entity.parent_entities) > 0:
            lines.append("   Parents: %s" % ", ".join([":inmanta:entity:`%s`" % x.get_full_name()
                                                       for x in entity.parent_entities]))
        lines.append("")

        attributes = {}
        if(entity.comment):
            result = parse_docstring(entity.comment)
            lines.extend(["   " + x for x in result["comment"]])
            lines.append("")
            attributes = result["attributes"]

        lines.extend(self.emit_attributes(entity, attributes))
        lines.extend(self.emit_implementations(entity))
        lines.append("")

        return lines

    def _get_modules(self, module_path):
        if os.path.exists(module_path) and module.Module.is_valid_module(module_path):
            mod = module.Module(None, module_path)
            return mod.get_all_submodules()
        return []

    def run(self):
        env = self.state.document.settings.env
        module_dir = env.config.inmanta_modules_dir

        args = []
        for arg in self.content:
            arg = arg.strip()
            if len(arg) > 0:
                args.append(arg)

        submodules = []
        name = args[0]
        module_path = os.path.join(module_dir, name)
        submodules.extend(self._get_modules(module_path))

        if "additional_modules" in self.options:
            for name in self.options["additional_modules"]:
                module_path = os.path.join(module_dir, name)
                submodules.extend(self._get_modules(module_path))

        lines = self.doc_compile(module_dir, args[0], submodules)

        result = ViewList()
        source_name = '<' + __name__ + '>'
        for line in lines:
            result.append(line, source_name)

        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, result, node)

        return node.children


class ConfigDomain(Domain):
    """inmanta.config domain."""
    name = 'inmanta.config'
    label = 'inmanta.config'
    object_types = {
        'configoption': ObjType('configuration option', 'option'),
    }
    directives = {
        'group': ConfigGroup,
        'option': ConfigOption,
    }
    roles = {
        'option': ConfigOptXRefRole(),
        'group': ConfigGroupXRefRole(),
    }
    initial_data = {
        'options': {},
        'groups': {},
    }

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        if typ == 'option':
            _, option_name = target.split('.', 1)
            return make_refnode(
                builder,
                fromdocname,
                env.domaindata['inmanta.config']['options'][target],
                target,
                contnode,
                option_name,
            )
        if typ == 'group':
            return make_refnode(
                builder,
                fromdocname,
                env.domaindata['inmanta.config']['groups'][target],
                target,
                contnode,
                target,
            )
        return None


class InmantaXRefRole(XRefRole):
    pass


class InmantaObject(ObjectDescription):
    def add_target_and_index(self, name, sig, signode):
        targetname = self.objtype + '-' + name
        if targetname not in self.state.document.ids:
            signode['names'].append(targetname)
            signode['ids'].append(targetname)
            signode['first'] = (not self.names)
            self.state.document.note_explicit_target(signode)

            objects = self.env.domaindata['inmanta']['objects']
            key = (self.objtype, name)
            if key in objects:
                self.state_machine.reporter.warning('duplicate description of %s %s, ' % (self.objtype, name) +
                                                    'other instance in ' + self.env.doc2path(objects[key]), line=self.lineno)
            objects[key] = self.env.docname
        indextext = self.get_index_text(self.objtype, name)
        if indextext:
            self.indexnode['entries'].append(('single', indextext, targetname, '', None))

    def get_index_text(self, objectname, name):
        return name


class Entity(InmantaObject):
    def handle_signature(self, sig, signode):
        signode += addnodes.desc_annotation("entity", "entity ")
        signode += addnodes.desc_addname(sig, sig)
        return sig


class Attribute(InmantaObject):
    def handle_signature(self, sig, signode):
        signode += addnodes.desc_annotation("attribute", "attribute ")
        typ, name = sig.split(" ")
        default = None
        if "=" in name:
            name, default = name.split("=")

        signode += addnodes.desc_type(typ, typ + " ")

        show_name = name
        if "." in name:
            _, show_name = name.split(".")
        signode += addnodes.desc_addname(name, show_name)

        if default is not None:
            signode += addnodes.desc_type(default, "=" + default)

        return name


class Relation(InmantaObject):
    def handle_signature(self, sig, signode):
        signode += addnodes.desc_annotation("relation", "relation ")
        typ, name, mult = sig.split(" ")
        signode += addnodes.desc_type(typ, typ + " ")

        show_name = name
        if "." in name:
            _, show_name = name.split(".")
        signode += addnodes.desc_addname(name, show_name)

        signode += addnodes.desc_type(mult, " " + mult)
        return name


class Implementation(InmantaObject):
    def handle_signature(self, sig, signode):
        signode += addnodes.desc_annotation("implementation", "implementation ")
        signode += addnodes.desc_addname(sig, sig)
        return sig


class InmantaDomain(Domain):
    name = "inmanta"
    label = "inmanta"

    object_types = {
        'module': ObjType(l_('module'), 'mod', 'obj'),
        'entity': ObjType(l_('entity'), 'func', 'obj'),
        'attribute': ObjType(l_('attribute'), 'attr', 'obj'),
        'relation': ObjType(l_('relation'), 'attr', 'obj'),
        'implementation': ObjType(l_('implementation'), 'attr', 'obj'),
    }
    directives = {
        'module': Entity,
        'entity': Entity,
        'attribute': Attribute,
        'relation': Relation,
        'implementation': Implementation,
    }
    roles = {
        'entity': InmantaXRefRole(),
        'attribute': InmantaXRefRole(),
        'relation': InmantaXRefRole(),
        'implementation': InmantaXRefRole(),
    }
    initial_data = {
        'objects': {},  # fullname -> docname, objtype
    }

    def clear_doc(self, docname):
        for (typ, name), doc in list(self.data['objects'].items()):
            if doc == docname:
                del self.data['objects'][typ, name]

    def merge_domaindata(self, docnames, otherdata):
        # XXX check duplicates
        for (typ, name), doc in otherdata['objects'].items():
            if doc in docnames:
                self.data['objects'][typ, name] = doc

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        objects = self.data['objects']
        for objtype in self.object_types.keys():
            if (objtype, target) in objects:
                return make_refnode(builder, fromdocname, objects[objtype, target], objtype + '-' + target,
                                    contnode, target + ' ' + objtype)

    def resolve_any_xref(self, env, fromdocname, builder, target,
                         node, contnode):
        objects = self.data['objects']
        results = []
        for objtype in self.object_types:
            if (objtype, target) in self.data['objects']:
                results.append(('inmanta:' + self.role_for_objtype(objtype),
                                make_refnode(builder, fromdocname, objects[objtype, target], objtype + '-' + target,
                                             contnode, target + ' ' + objtype)))
        return results

    def get_objects(self):
        for (typ, name), docname in self.data['objects'].items():
            yield name, name, typ, docname, typ + '-' + name, 1


def setup(app):
    app.add_directive('show-options', ShowOptionsDirective)
    app.add_domain(ConfigDomain)

    app.add_config_value('inmanta_modules_dir', 'modules', rebuild=None)
    app.add_directive('inmanta-module', ShowModule)
    app.add_domain(InmantaDomain)
