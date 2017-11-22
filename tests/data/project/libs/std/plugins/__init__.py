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
import logging
from operator import attrgetter
from itertools import chain
from collections import defaultdict


from inmanta.ast import OptionalValueException, RuntimeException
from inmanta.execute.proxy import DynamicProxy, UnknownException
from inmanta.execute.util import Unknown, NoneValue
from inmanta.export import dependency_manager
from inmanta.plugins import plugin, Context
from inmanta.export import unknown_parameters
from inmanta import resources
from inmanta.module import Project
from inmanta.config import Config


from copy import copy
from inmanta.ast import NotFoundException
from jinja2 import Environment, FileSystemLoader, PrefixLoader
from jinja2.exceptions import UndefinedError
from jinja2.runtime import Undefined
import jinja2


@plugin
def unique_file(prefix: "string", seed: "string", suffix: "string", length: "number"=20) -> "string":
    return prefix + hashlib.md5(seed.encode("utf-8")).hexdigest() + suffix


tcache = {}

engine_cache = None


class JinjaDynamicProxy(DynamicProxy):

    def __init__(self, instance):
        super(JinjaDynamicProxy, self).__init__(instance)

    @classmethod
    def return_value(cls, value):
        if value is None:
            return None

        if isinstance(value, NoneValue):
            return None

        if isinstance(value, Unknown):
            raise UnknownException(value)

        if isinstance(value, (str, tuple, int, float, bool)):
            return copy(value)

        if isinstance(value, DynamicProxy):
            return value

        if hasattr(value, "__len__"):
            return SequenceProxy(value)

        if hasattr(value, "__call__"):
            return CallProxy(value)

        return cls(value)

    def __getattr__(self, attribute):
        instance = self._get_instance()
        if hasattr(instance, "get_attribute"):
            try:
                value = instance.get_attribute(attribute).get_value()
                return JinjaDynamicProxy.return_value(value)
            except (OptionalValueException, NotFoundException):
                return Undefined("variable %s not set on %s" % (attribute, instance), instance, attribute)
        else:
            # A native python object such as a dict
            return getattr(instance, attribute)


class SequenceProxy(JinjaDynamicProxy):

    def __init__(self, iterator):
        JinjaDynamicProxy.__init__(self, iterator)

    def __getitem__(self, key):
        instance = self._get_instance()
        if isinstance(key, str):
            raise RuntimeException(self, "can not get a attribute %s, %s is a list" % (key, self._get_instance()))

        return JinjaDynamicProxy.return_value(instance[key])

    def __len__(self):
        return len(self._get_instance())

    def __iter__(self):
        instance = self._get_instance()

        return IteratorProxy(instance.__iter__())


class CallProxy(JinjaDynamicProxy):
    """
        Proxy a value that implements a __call__ function
    """

    def __init__(self, instance):
        JinjaDynamicProxy.__init__(self, instance)

    def __call__(self, *args, **kwargs):
        instance = self._get_instance()

        return instance(*args, **kwargs)


class IteratorProxy(JinjaDynamicProxy):
    """
        Proxy an iterator call
    """

    def __init__(self, iterator):
        JinjaDynamicProxy.__init__(self, iterator)

    def __iter__(self):
        return self

    def __next__(self):
        i = self._get_instance()
        return JinjaDynamicProxy.return_value(next(i))


class ResolverContext(jinja2.runtime.Context):

    def resolve(self, key):
        resolver = self.parent["{{resolver"]
        try:
            raw = resolver.lookup(key)
            return JinjaDynamicProxy.return_value(raw.get_value())
        except NotFoundException:
            return super(ResolverContext, self).resolve(key)
        except OptionalValueException as e:
            return self.environment.undefined("variable %s not set on %s" % (resolver, key), resolver, key, e)


def _get_template_engine(ctx):
    """
        Initialize the template engine environment
    """
    global engine_cache
    if engine_cache is not None:
        return engine_cache

    loader_map = {}
    loader_map[""] = FileSystemLoader(os.path.join(Project.get().project_path, "templates"))
    for name, module in Project.get().modules.items():
        template_dir = os.path.join(module._path, "templates")
        if os.path.isdir(template_dir):
            loader_map[name] = FileSystemLoader(template_dir)

    # init the environment
    env = Environment(loader=PrefixLoader(loader_map), undefined=jinja2.StrictUndefined)
    env.context_class = ResolverContext

    # register all plugins as filters
    for name, cls in ctx.get_compiler().get_plugins().items():
        def curywrapper(func):
            def safewrapper(*args):
                return JinjaDynamicProxy.return_value(func(*args))
            return safewrapper
        env.filters[name.replace("::", ".")] = curywrapper(cls)

    engine_cache = env
    return env


@plugin("template")
def template(ctx: Context, path: "string"):
    """
        Execute the template in path in the current context. This function will
        generate a new statement that has dependencies on the used variables.
    """
    jinja_env = _get_template_engine(ctx)

    if path in tcache:
        template = tcache[path]
    else:
        template = jinja_env.get_template(path)
        tcache[path] = template

    resolver = ctx.get_resolver()

    try:
        out = template.render({"{{resolver": resolver})
        return out
    except UndefinedError as e:
        raise NotFoundException(ctx.owner, None, e.message)


@dependency_manager
def dir_before_file(model, resources):
    """
        If a file is defined on a host, then make the file depend on its parent directory
    """
    # loop over all resources to find files and dirs
    per_host = defaultdict(list)
    per_host_dirs = defaultdict(list)
    for _id, resource in resources.items():
        if resource.id.get_entity_type() == "std::File" or resource.id.get_entity_type() == "std::Directory":
            per_host[resource.model.host].append(resource)

        if resource.id.get_entity_type() == "std::Directory":
            per_host_dirs[resource.model.host].append(resource)

    # now add deps per host
    for host, files in per_host.items():
        for hfile in files:
            for pdir in per_host_dirs[host]:
                if hfile.path != pdir.path and hfile.path[:len(pdir.path)] == pdir.path:
                    # Make the File resource require the directory
                    hfile.requires.add(pdir)


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
def replace(string: "string", old: "string", new: "string") -> "string":
    return string.replace(old, new)


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

        :param any: A dummy argument to be able to use this function as a filter
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

        :param expression: An expression that accepts one arguments and
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

        :param expression: An expression that accepts one argument and
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

        :param expression: An expression that accepts one arguments and
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

        :param expression: The expression that selects the attributes of the
            items in the source list that are used to determine the order
            of the returned list.

        :param comparator: An optional expression that compares two items.
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
    """
    new_list = []

    for item in item_list:
        new_list.append(lambda x: getattr(x, attr))

    return new_list


@plugin
def select_many(item_list: "list", expression: "expression",
                selector_expression: "expression"=None) -> "list":
    """
        This query method is similar to the select query but it merges
        the results into one list.

        :param expresion: An expression that returns the item that is to be
            included in the resulting list. If that item is a list itself
            it is merged into the result list. The first argument of the
            expression is the item in the source sequence.

        :param selector_expression: This optional arguments allows to
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

        :param expression: An expression that returns true or false
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

        :param expr_list: A list of tupples where the first item is the attr
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

    if parts[0] == "":
        module_path = Project.get().project_path
    elif parts[0] not in modules:
        raise Exception("Module %s does not exist for path %s" %
                        (parts[0], path))
    else:
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
        raise Exception("%s isn't a valid file (%s)" % (path, filename))

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
    if member.name == family:
        return True

    parent = member
    try:
        while parent.family is not None:
            if parent.name == family:
                return True

            parent = parent.family
    except OptionalValueException:
        pass

    return False


@plugin
def getfact(context: Context, resource: "any", fact_name: "string", default_value: "any"=None) -> "any":
    """
        Retrieve a fact of the given resource
    """
    resource_id = resources.to_id(resource)
    if resource_id is None:
        raise Exception("Facts can only be retreived from resources.")

    # Special case for unit testing and mocking
    if hasattr(context.compiler, "refs") and "facts" in context.compiler.refs:
        if resource_id in context.compiler.refs["facts"] and fact_name in context.compiler.refs["facts"][resource_id]:
            return context.compiler.refs["facts"][resource_id][fact_name]

        fact_value = Unknown(source=resource)
        unknown_parameters.append({"resource": resource_id, "parameter": fact_name, "source": "fact"})

        if default_value is not None:
            return default_value
        return fact_value
    # End special case

    fact_value = None
    try:
        client = context.get_client()

        env = Config.get("config", "environment", None)
        if env is None:
            raise Exception("The environment of this model should be configured in config>environment")

        def call():
            return client.get_param(tid=env, id=fact_name, resource_id=resource_id)

        result = context.run_sync(call)

        if result.code == 200:
            fact_value = result.result["parameter"]["value"]
        else:
            logging.getLogger(__name__).info("Param %s of resource %s is unknown", fact_name, resource_id)
            fact_value = Unknown(source=resource)
            unknown_parameters.append({"resource": resource_id, "parameter": fact_name, "source": "fact"})

    except ConnectionRefusedError:
        logging.getLogger(__name__).warning("Param %s of resource %s is unknown because connection to server was refused",
                                            fact_name, resource_id)
        fact_value = Unknown(source=resource)
        unknown_parameters.append({"resource": resource_id, "parameter": fact_name, "source": "fact"})

    if isinstance(fact_value, Unknown) and default_value is not None:
        return default_value

    return fact_value


@plugin
def environment() -> "string":
    """
        Return the environment id
    """
    env = str(Config.get("config", "environment", None))

    if env is None:
        raise Exception("The environment of this model should be configured in config>environment")

    return str(env)


@plugin
def environment_name(ctx: Context) -> "string":
    """
        Return the name of the environment (as defined on the server)
    """
    env = environment()

    def call():
        return ctx.get_client().get_environment(id=env)
    result = ctx.run_sync(call)
    if result.code != 200:
        return Unknown(source=env)
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
def is_set(obj: "any", attribute: "string") -> "bool":
    try:
        getattr(obj, attribute)
    except Exception:
        return False
    return True


@plugin
def server_ca() -> "string":
    filename = Config.get("compiler_rest_transport", "ssl_ca_cert_file", "")
    if filename == "":
        return ""
    if filename is None:
        raise Exception("%s does not exist" % filename)

    if not os.path.isfile(filename):
        raise Exception("%s isn't a valid file" % filename)

    file_fd = open(filename, 'r')
    if file_fd is None:
        raise Exception("Unable to open file %s" % filename)

    content = file_fd.read()
    return content


@plugin
def server_token(context: Context, client_types: "string[]" = ["agent"]) -> "string":
    token = Config.get("compiler_rest_transport", "token", "")
    if token == "":
        return ""

    # Request a new token for this agent
    token = ""
    try:
        client = context.get_client()

        env = Config.get("config", "environment", None)
        if env is None:
            raise Exception("The environment of this model should be configured in config>environment")

        def call():
            return client.create_token(tid=env, client_types=list(client_types), idempotent=True)

        result = context.run_sync(call)

        if result.code == 200:
            token = result.result["token"]
        else:
            logging.getLogger(__name__).warning("Unable to get a new token")
            raise Exception("Unable to get a valid token")
    except ConnectionRefusedError:
        logging.getLogger(__name__).exception("Unable to get a new token")
        raise Exception("Unable to get a valid token")

    return token


@plugin
def server_port() -> "number":
    return Config.get("compiler_rest_transport", "port", 8888)


@plugin
def get_env(name: "string", default_value: "string"=None) -> "string":
    env = os.environ
    if name in env:
        return env[name]
    elif default_value is not None:
        return default_value
    else:
        return Unknown(source=name)


@plugin
def get_env_int(name: "string", default_value: "number"=None) -> "number":
    env = os.environ
    if name in env:
        return int(env[name])
    elif default_value is not None:
        return default_value
    else:
        return Unknown(source=name)


@plugin
def is_instance(ctx: Context, obj: "any", cls: "string") -> "bool":
    t = ctx.get_type(cls)
    try:
        t.validate(obj._get_instance())
    except RuntimeException:
        return False
    return True


@plugin("if")
def inlineif(expr: "bool", true_value: "any", false_value: "any") -> "any":
    """
        An inline if expression that can also handle nullable booleans

        :attr expr: The if expression to determine the true or false.
        :attr true_value: The value when expr is true
        :attr false_value: The value when the expr is not true
    """
    if expr:
        return true_value
    return false_value
