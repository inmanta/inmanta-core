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

import hashlib
import os
import random
import re
import time
import uuid
from operator import attrgetter
from itertools import chain

from inmanta.ast import OptionalValueException, RuntimeException
from inmanta.ast.statements import ExpressionStatement
from inmanta.ast.variables import Reference
from inmanta.execute.proxy import DynamicProxy, UnknownException
from inmanta.execute.util import Unknown
from inmanta.export import dependency_manager
from inmanta.plugins import plugin, Context, PluginMeta
from inmanta.resources import Resource
from inmanta.module import Project
from inmanta.facts import get_fact
from inmanta import protocol
from inmanta.config import Config


from jinja2 import Environment, meta, FileSystemLoader, PrefixLoader, Template
from jinja2.defaults import DEFAULT_NAMESPACE


@plugin
def unique_file(prefix: "string", seed: "string", suffix: "string", length: "number"=20) -> "string":
    return prefix + hashlib.md5(seed.encode("utf-8")).hexdigest() + suffix


vcache = {}
tcache = {}


class TemplateStatement(ExpressionStatement):
    """
        Evaluates a template
    """

    def __init__(self, env, template_file=None, template_content=None):
        ExpressionStatement.__init__(self)
        self._template = template_file
        self._content = template_content
        self._env = env
        self._requires = self._get_variables()

    def normalize(self, resolver):
        pass

    def requires(self):
        return self._requires

    def requires_emit(self, resolver, queue):
        return {k: resolver.lookup(k) for k in self._requires}

    def is_file(self):
        """
            Use a file?
        """
        return self._template is not None and self._content is None

    def _get_variables(self):
        """
            Get all variables that are unsresolved
        """
        if self._template in vcache:
            return vcache[self._template]

        if self.is_file():
            source = self._env.loader.get_source(self._env, self._template)[0]
        else:
            source = self._content

        # Parse here, later again,....
        ast = self._env.parse(source)
        variables = meta.find_undeclared_variables(ast)
        for x in DEFAULT_NAMESPACE:
            if x in variables:
                variables.remove(x)
        vcache[self._template] = variables

        return variables

    def execute(self, requires, resolver, queue):
        """
            Execute this function
        """
        if self._template in tcache:
            template = tcache[self._template]
        elif self.is_file():
            template = self._env.get_template(self._template)
            tcache[self._template] = template
        else:
            template = Template(self._content)
            tcache[self._template] = template

        variables = {}
        try:
            for name in self._requires:
                variables[name] = DynamicProxy.return_value(requires[name])
            return template.render(variables)
        except UnknownException as e:
            return e.unknown

    def __repr__(self):
        return "Template(%s)" % self._template


engine_cache = None


def _get_template_engine(ctx):
    """
        Initialize the template engine environment
    """
    global engine_cache
    if engine_cache is not None:
        return engine_cache

    loader_map = {}
    for name, module in Project.get().modules.items():
        template_dir = os.path.join(module._path, "templates")
        if os.path.isdir(template_dir):
            loader_map[name] = FileSystemLoader(template_dir)

    # init the environment
    env = Environment(loader=PrefixLoader(loader_map))

    # register all plugins as filters
    for name, cls in ctx.get_compiler().get_plugins().items():
        env.filters[name.replace("::", ".")] = cls

    engine_cache = env
    return env


@plugin("template", emits_statements=True)
def template(ctx: Context, path: "string"):
    """
        Execute the template in path in the current context. This function will
        generate a new statement that has dependencies on the used variables.
    """
    jinja_env = _get_template_engine(ctx)

    stmt = TemplateStatement(jinja_env, template_file=path)
    stmt.namespace = ["std"]

    ctx.emit_expression(stmt)


@dependency_manager
def dir_before_file(model, resources):
    """
        If a file is defined on a host, then make the file depend on its parent directory
    """
    # loop over all resources to find files
    for _id, resource in resources.items():

        if resource.is_type("std::File"):
            model = resource.model
            host = model.host

            for dir in host.directories:
                dir_res = Resource.get_resource(dir)
                if dir_res is not None and os.path.dirname(resource.path) == dir_res.path:
                    # Make the File resource require the directory
                    resource.requires.add(dir_res)


def get_passwords(pw_file):
    records = {}
    if os.path.exists(pw_file):
        with open(pw_file, "r") as fd:

            for line in fd.readlines():
                line = line.strip()
                if len(line) > 2:
                    i = line.index("=")

                    try:
                        records[line[:i].strip()] = line[i + 1:].strip()
                    except ValueError:
                        pass

    return records


def save_passwords(pw_file, records):
    with open(pw_file, "w+") as fd:
        for key, value in records.items():
            fd.write("%s=%s\n" % (key, value))


@plugin
def generate_password(context: Context, pw_id: "string", length: "number"=20) -> "string":
    """
    Generate a new random password and store it in the data directory of the
    project. On next invocations the stored password will be used.

    :param pw_id: The id of the password to identify it.
    :param length: The length of the password, default length is 20
    """
    data_dir = context.get_data_dir()
    pw_file = os.path.join(data_dir, "passwordfile.txt")

    if "=" in pw_id:
        raise Exception("The password id cannot contain =")

    records = get_passwords(pw_file)

    if pw_id in records:
        return records[pw_id]

    rnd = random.SystemRandom()
    pw = ""
    while len(pw) < length:
        x = chr(rnd.randint(33, 126))
        if re.match("[A-Za-z0-9]", x) is not None:
            pw += x

    # store the new value
    records[pw_id] = pw
    save_passwords(pw_file, records)

    return pw


@plugin
def password(context: Context, pw_id: "string") -> "string":
    """
        Retrieve the given password from a password file. It raises an exception when a password is not found

        :param pw_id: The id of the password to identify it.
    """
    data_dir = context.get_data_dir()
    pw_file = os.path.join(data_dir, "passwordfile.txt")

    if "=" in pw_id:
        raise Exception("The password id cannot contain =")

    records = get_passwords(pw_file)

    if pw_id in records:
        return records[pw_id]

    else:
        raise Exception("Password %s does not exist in file %s" % (pw_id, pw_file))


@plugin("print")
def printf(message: "any"):
    """
        Print the given message to stdout
    """
    print(message)


@plugin
def equals(arg1: "any", arg2: "any", desc: "string"=None):
    """
        Compare arg1 and arg2
    """
    if arg1 != arg2:
        if desc is not None:
            raise AssertionError("%s != %s: %s" % (arg1, arg2, desc))
        else:
            raise AssertionError("%s != %s" % (arg1, arg2))


@plugin("assert")
def assert_function(expression: "bool", message: "string"=""):
    """
        Raise assertion error is expression is false
    """
    if not expression:
        raise AssertionError("Assertion error: " + message)


@plugin
def delay(x: "any") -> "any":
    """
        Delay evaluation
    """
    return x


@plugin
def get(ctx: Context, path: "string") -> "any":
    """
        This function return the variable with given string path
    """
    parts = path.split("::")

    module = parts[0:-1]
    cls_name = parts[-1]

    var = ctx.scope.get_variable(cls_name, module)
    return var.value


@plugin
def select(objects: "list", attr: "string") -> "list":
    """
        Return a list with the select attributes
    """
    r = []
    for obj in objects:
        r.append(getattr(obj, attr))

    return r


@plugin
def item(objects: "list", index: "number") -> "list":
    """
        Return a list that selects the item at index from each of the sublists
    """
    r = []
    for obj in objects:
        r.append(obj[index])

    return r


@plugin
def key_sort(items: "list", key: "any") -> "list":
    """
        Sort an array of object on key
    """
    if isinstance(key, tuple):
        return sorted(items, key=attrgetter(*key))

    return sorted(items, key=attrgetter(key))


@plugin
def timestamp(dummy: "any"=None) -> "number":
    """
        Return an integer with the current unix timestamp

        @param any: A dummy argument to be able to use this function as a filter
    """
    return int(time.time())


@plugin
def capitalize(string: "string") -> "string":
    """
        Capitalize the given string
    """
    return string.capitalize()


@plugin
def type(obj: "any") -> "any":
    value = obj.value
    return value.type().__definition__


@plugin
def is_instance(ctx: Context, obj: "any", cls: "string") -> "bool":
    t = ctx.get_type(cls)
    try:
        t.validate(obj._get_instance())
    except RuntimeException:
        return False
    return True


@plugin
def sequence(i: "number", start: "number"=0, offset: "number"=0) -> "list":
    """
        Return a sequence of i numbers, starting from zero or start if supplied.
    """
    return list(range(start, int(i) + start - offset))


@plugin
def inlineif(conditional: "bool", a: "any", b: "any") -> "any":
    """
        An inline if
    """
    if conditional:
        return a
    return b


@plugin
def at(objects: "list", index: "number") -> "any":
    """
        Get the item at index
    """
    return objects[int(index)]


@plugin
def attr(obj: "any", attr: "string") -> "any":
    return getattr(obj, attr)


@plugin
def isset(value: "any") -> "bool":
    """
        Returns true if a value has been set
    """
    return value is not None


@plugin
def bootstrap(context: Context) -> "bool":
    if "bootstrap" not in context.compiler.config["config"]:
        return False
    value = context.compiler.config["config"].getboolean("bootstrap")
    return value


@plugin
def objid(value: "any") -> "string":
    return str((value._get_instance(), str(id(value._get_instance())), value._get_instance().__class__))


@plugin
def first_of(context: Context, value: "list", type_name: "string") -> "any":
    """
        Return the first in the list that has the given type
    """
    for item in value:
        d = item.type().__definition__
        name = "%s::%s" % (d.namespace, d.name)

        if name == type_name:
            return item

    return None


@plugin
def any(item_list: "list", expression: "expression") -> "bool":
    """
        This method returns true when at least on item evaluates expression
        to true, otherwise it returns false

        @param expression: An expression that accepts one arguments and
            returns true or false
    """
    for item in item_list:
        if expression(item):
            return True
    return False


@plugin
def all(item_list: "list", expression: "expression") -> "bool":
    """
        This method returns false when at least one item does not evaluate
        expression to true, otherwise it returns true

        @param expression: An expression that accepts one argument and
            returns true or false
    """
    for item in item_list:
        if not expression(item):
            return False
    return True


@plugin
def count(item_list: "list") -> "number":
    """
        Returns the number of elements in this list
    """
    return len(item_list)


@plugin
def each(item_list: "list", expression: "expression") -> "list":
    """
        Iterate over this list executing the expression for each item.

        @param expression: An expression that accepts one arguments and
            is evaluated for each item. The returns value of the expression
            is placed in a new list
    """
    new_list = []

    for item in item_list:
        value = expression(item)
        new_list.append(value)

    return new_list


@plugin
def order_by(item_list: "list", expression: "expression"=None, comparator: "expression"=None) -> "list":
    """
        This operation orders a list using the object returned by
        expression and optionally using the comparator function to determine
        the order.

        @param expression: The expression that selects the attributes of the
            items in the source list that are used to determine the order
            of the returned list.

        @param comparator: An optional expression that compares two items.
    """
    expression_cache = {}

    def get_from_cache(item):
        """
            Function that is used to retrieve cache results
        """
        if item in expression_cache:
            return expression_cache[item]
        else:
            data = expression(item)
            expression_cache[item] = data
            return data

    def sort_cmp(item_a, item_b):
        """
            A function that uses the optional expressions to sort item_a list
        """
        if expression is not None:
            a_data = get_from_cache(item_a)
            b_data = get_from_cache(item_b)
        else:
            a_data = item_a
            b_data = item_b

        if comparator is not None:
            return comparator(a_data, b_data)
        else:
            if a_data > b_data:
                return 1
            elif b_data > a_data:
                return -1
            return 0

    # sort
    return sorted(item_list, sort_cmp)


@plugin
def unique(item_list: "list") -> "bool":
    """
        Returns true if all items in this sequence are unique
    """
    seen = set()
    for item in item_list:
        if item in seen:
            return False
        seen.add(item)

    return True


@plugin
def select_attr(item_list: "list", attr: "string") -> "list":
    """
        This query method projects the list onto a new list by transforming
        the list as defined in the expression.

        @param expression: An expression that returns the item that is to be
            included in the resulting list. The first argument of the
            expression is the item in the source sequence.
    """
    new_list = []

    if isinstance(attr, str):
        expression = lambda x: getattr(x, attr)

    for item in item_list:
        new_list.append(expression(item))

    return new_list


@plugin
def select_many(item_list: "list", expression: "expression",
                selector_expression: "expression"=None) -> "list":
    """
        This query method is similar to the select query but it merges
        the results into one list.

        @param expresion: An expression that returns the item that is to be
            included in the resulting list. If that item is a list itself
            it is merged into the result list. The first argument of the
            expression is the item in the source sequence.

        @param selector_expression: This optional arguments allows to
            provide an expression that projects the result of the first
            expression. This selector expression is equivalent to what the
            select method expects. If the returned item of expression is
            not a list this expression is not applied.
    """
    new_list = []

    for item in item_list:
        result = expression(item)

        if not hasattr(result, "__iter__"):
            new_list.append(result)
        else:
            if selector_expression:
                for result_item in result:
                    new_list.append(selector_expression(result_item))
            else:
                new_list.extend(result)

    return new_list


@plugin
def where(item_list: "list", expression: "expression") -> "list":
    """
        This query method selects the items in the list that evaluate the
        expression to true.

        @param expression: An expression that returns true or false
            to determine if an item from the list is included. The first
            argument of the expression is the item that is to be evaluated.
            The second optional argument is the index of the item in the
            list.
    """
    new_list = []
    for index in range(len(item_list)):
        item = item_list[index]

        if expression(item):
            new_list.append(item)

    return new_list


@plugin
def where_compare(item_list: "list", expr_list: "list") -> "list":
    """
        This query selects items in a list but uses the tupples in expr_list
        to select the items.

        @param expr_list: A list of tupples where the first item is the attr
            name and the second item in the tupple is the value
    """
    new_list = []

    new_expr_list = []
    for i in range(0, len(expr_list), 2):
        new_expr_list.append((expr_list[i], expr_list[i + 1]))

    for index in range(len(item_list)):
        item = item_list[index]

        for attr, value in new_expr_list:
            if getattr(item, attr) == value:
                new_list.append(item)

    return new_list


@plugin
def flatten(item_list: "list") -> "list":
    """
        Flatten this list
    """
    return list(chain.from_iterable(item_list))


@plugin
def split(string_list: "string", delim: "string") -> "list":
    """
        Split the given string into a list

        :param string_list: The list to split into parts
        :param delim: The delimeter to split the text by
    """
    return string_list.split(delim)


def determine_path(ctx, module_dir, path):
    """
        Determine the real path based on the given path
    """
    parts = path.split(os.path.sep)

    modules = Project.get().modules

    if parts[0] not in modules:
        raise Exception("Module %s does not exist for path %s" %
                        (parts[0], path))

    module_path = modules[parts[0]]._path

    return os.path.join(module_path, module_dir, os.path.sep.join(parts[1:]))


def get_file_content(ctx, module_dir, path):
    """
        Get the contents of a file
    """
    filename = determine_path(ctx, module_dir, path)

    if filename is None:
        raise Exception("%s does not exist" % path)

    if not os.path.isfile(filename):
        raise Exception("%s isn't a valid file" % path)

    file_fd = open(filename, 'r')
    if file_fd is None:
        raise Exception("Unable to open file %s" % filename)

    content = file_fd.read()
    file_fd.close()

    return content


@plugin
def source(ctx: Context, path: "string") -> "string":
    """
        Return the textual contents of the given file
    """
    return get_file_content(ctx, 'files', path)


@plugin
def file(ctx: Context, path: "string") -> "string":
    """
        Return the textual contents of the given file
    """
    filename = determine_path(ctx, 'files', path)
    any
    if filename is None:
        raise Exception("%s does not exist" % path)

    if not os.path.isfile(filename):
        raise Exception("%s isn't a valid file" % path)

    return "imp-module-source:file://" + os.path.abspath(filename)


@plugin
def familyof(member: "std::OS", family: "string") -> "bool":
    """
        Determine if member is a member of the given operating system family
    """
    try:
        if member.name == family:
            return True

        parent = member
        while parent.family is not None:
            if parent.name == family:
                return True

            parent = parent.family
    except OptionalValueException:
        return False

    return False


@plugin
def getfact(resource: "any", fact_name: "string", default_value: "any"=None) -> "any":
    """
        Retrieve a fact of the given resource
    """
    return get_fact(resource, fact_name, default_value)


@plugin
def environment() -> "string":
    """
        Return the environment id
    """
    env = Config.get("config", "environment", None)

    if env is None:
        raise Exception("The environment of this model should be configured in config>environment")

    try:
        uuid.UUID(env)
    except ValueError:
        raise Exception("The environment id should be a valid UUID.")

    return env


@plugin
def environment_name(ctx: Context) -> "string":
    """
        Return the name of the environment (as defined on the server)
    """
    env_id = environment()

    def call():
        return ctx.get_client().get_environment(id=env_id)
    result = ctx.run_sync(call)
    if result.code != 200:
        return Unknown(source=env_id)
    return result.result["environment"]["name"]


@plugin
def environment_server(ctx: Context) -> "string":
    """
        Return the address of the management server
    """
    client = ctx.get_client()
    server_url = client._transport_instance._get_client_config()
    match = re.search("^http[s]?://([^:]+):", server_url)
    if match is not None:
        return match.group(1)
    return Unknown(source=server_url)


@plugin
def server_username() -> "string":
    """
        Return the username of the management server
    """
    return Config.get("compiler_rest_transport", "username", "")


@plugin
def server_password() -> "string":
    """
        Return the password of the management server
    """
    return Config.get("compiler_rest_transport", "password", "")


@plugin
def server_ca(ctx: Context) -> "string":
    """
        Return the password of the management server
    """
    out = Config.get("compiler_rest_transport", "ssl_ca_cert_file", None)
    if out is None:
        return ""

    file_fd = open(out, 'r')
    if file_fd is None:
        raise Exception("Unable to open file %s" % out)

    content = file_fd.read()
    file_fd.close()

    return content


@plugin
def is_set(obj: "any", attribute: "string") -> "bool":
    try:
        getattr(obj, attribute)
    except:
        return False
    return True
