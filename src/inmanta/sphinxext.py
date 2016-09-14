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

import importlib

from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain
from sphinx.domains import ObjType
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode
from sphinx.util.nodes import nested_parse_with_titles
from inmanta.config import Config


def _list_table(headers, data, title='', columns=None):
    """Build a list-table directive.

    :param add: Function to add one row to output.
    :param headers: List of header values.
    :param data: Iterable of row data, yielding lists or tuples with rows.
    """
    yield '.. list-table:: %s' % title
    yield '   :header-rows: 1'
    if columns:
        yield '   :widths: %s' % (','.join(str(c) for c in columns))
    yield ''
    yield '   - * %s' % headers[0]
    for h in headers[1:]:
        yield '     * %s' % h
    for row in data:
        yield '   - * %s' % row[0]
        for r in row[1:]:
            yield '     * %s' % r
    yield ''


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

        type = opt.get_type()
        if type:
            yield _indent(':Type: %s' % type)
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


class ShowOptionsDirective(rst.Directive):

    option_spec = {
        'split-namespaces': directives.flag,
        'config-file': directives.unchanged,
    }

    has_content = True

    def run(self):
        env = self.state.document.settings.env
        app = env.app

        namespaces = [
            c.strip()
            for c in self.content
            if c.strip()
        ]
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


class ConfigGroupXRefRole(XRefRole):
    "Handles :inmanta.config:group: roles pointing to configuration groups."

    def __init__(self):
        super(ConfigGroupXRefRole, self).__init__(
            warn_dangling=True,
        )

    def process_link(self, env, refnode, has_explicit_title, title, target):
        # The anchor for the group link is the group name.
        return target, target


class ConfigOptXRefRole(XRefRole):
    "Handles :inmanta.config:option: roles pointing to configuration options."

    def __init__(self):
        super(ConfigOptXRefRole, self).__init__(
            warn_dangling=True,
        )

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

    def resolve_xref(self, env, fromdocname, builder,
                     typ, target, node, contnode):
        if typ == 'option':
            group_name, option_name = target.split('.', 1)
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


def setup(app):
    app.add_directive('show-options', ShowOptionsDirective)
    app.add_domain(ConfigDomain)
