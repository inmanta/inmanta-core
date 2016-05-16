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

from distutils.version import StrictVersion, Version
import glob
import imp
import logging
import os
from os.path import sys
import re
from subprocess import TimeoutExpired
import subprocess
from urllib3 import util, exceptions
import tempfile
import shutil

from pkg_resources import parse_version, parse_requirements, Requirement

import yaml
import impera
from impera import env
from impera.config import Config
from impera.ast import Namespace
from impera import plugins
from impera.parser.plyInmantaParser import parse


LOGGER = logging.getLogger(__name__)


class InvalidModuleException(Exception):
    """
        This exception is raised if a module is invalid
    """


class InvalidModuleFileException(Exception):
    """
        This exception is raised if a module file is invalid
    """


class ProjectNotFoundExcpetion(Exception):
    """
        This exception is raised when Impera is unable to find a valid project
    """


class GitProvider:

    def clone(self, src, dest):
        pass

    def fetch(self, repo):
        pass

    def get_all_tags(self, repo):
        pass


class CLIGitProvider(GitProvider):

    def clone(self, src, dest):
        subprocess.check_call(["git", "clone", src, dest])

    def fetch(self, repo):
        subprocess.check_call(["git", "fetch"], cwd=repo)

    def get_all_tags(self, repo):
        return subprocess.check_output(["git", "tag"], cwd=repo).decode("utf-8").splitlines()

    def checkout_tag(self, repo, tag):
        subprocess.check_call(["git", "checkout", tag], cwd=repo)


gitprovider = CLIGitProvider()


class ModuleRepo:

    def clone(self, name: str, dest: str) -> bool:
        raise NotImplementedError("Abstract method")

    def path_for(self, name: str):
        # same class is used for search parh and remote repos, perhaps not optimal
        raise NotImplementedError("Abstract method")


class CompositeModuleRepo(ModuleRepo):

    def __init__(self, children):
        self.children = children

    def clone(self, name: str, dest: str) -> bool:
        for child in self.children:
            if child.clone(name, dest):
                return True
        return False

    def path_for(self, name: str):
        for child in self.children:
            result = child.path_for(name)
            if result is not None:
                return result
        return None


class LocalFileRepo(ModuleRepo):

    def __init__(self, root):
        self.root = os.path.abspath(root)

    def clone(self, name: str, dest: str) -> bool:
        try:
            gitprovider.clone(os.path.join(self.root, name), os.path.join(dest, name))
            return True
        except:
            LOGGER.debug("could not clone repo", exc_info=True)
            return False

    def path_for(self, name: str):
        path = os.path.join(self.root, name)
        if os.path.exists(path):
            return path
        return None


class RemoteRepo(ModuleRepo):

    def __init__(self, baseurl):
        self.baseurl = baseurl

    def clone(self, name: str, dest: str) -> bool:
        try:
            gitprovider.clone(self.baseurl + name, os.path.join(dest, name))
            return True
        except:
            LOGGER.debug("could not clone repo", exc_info=True)
            return False

    def path_for(self, name: str):
        raise NotImplementedError("Should only be called on local repos")


def makeRepo(path):
    if ":" in path:
        return RemoteRepo(path)
    else:
        return LocalFileRepo(path)


class GitVersioned:
    """
        Commons superclass for projects and modules, which are both versioned by git
    """

    def __init__(self, path):
        """
            @param path: root git directory
        """
        self._path = path

    def get_name(self):
        raise NotImplemented()

    name = property(get_name)

    def get_scm_url(self):
        try:
            return subprocess.check_output(["git", "config", "--get", "remote.origin.url"],
                                           cwd=self._path).decode("utf-8") .strip()
        except Exception:
            return None

    def get_scm_version(self):
        try:
            return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self._path).decode("utf-8") .strip()
        except Exception:
            return None

    def get_scm_branch(self):
        try:
            return subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                           cwd=self._path).decode("utf-8") .strip()
        except Exception:
            return None

    def get_scm_resolve(self, refspec):
        try:
            return subprocess.check_output(["git", "rev-parse", refspec],
                                           cwd=self._path, stderr=subprocess.DEVNULL).decode("utf-8") .strip()
        except Exception:
            return None

    def get_scm_is_ancestor(self, refspec):
        try:
            return subprocess.call(["git", "merge-base", "--is-ancestor", refspec, "HEAD"],
                                   cwd=self._path) == 0
        except Exception as e:
            print(e)
            return None

    def verify_requires(self, module_map: dict) -> bool:
        """
            Check if all the required modules for this module have been loaded
        """

        for require, defs in self.requires().items():
            if require not in module_map:
                print("Module %s requires the %s module that has not been loaded" % (
                    self._path, require))
                return False

            source = defs["source"]
            version = defs["version"]

            module = module_map[require]
            if not module.verify_require(source, version):
                print("Module %s requires module %s with version %s which is not loaded" %
                      (self.name, require, version.strip()))
                return False

        return True

    def verify_require(self, source_spec: str, version_spec: str) -> bool:
        """
            Verify if this module satisfies the given source and version spec
        """
        # TODO: verify source
        version_spec = version_spec.strip("\"")

        gte = version_spec.startswith(">=")

        if gte:
            version_spec = version_spec[2:]

        return self.compare_version(version_spec.strip(), gte)

    def compare_version(self, version_spec: str, gte: bool) -> bool:
        version = self.get_scm_resolve(version_spec)

        if version is None:
            LOGGER.warning("Module %s does not have version %s"
                           % (self._path, version_spec))
            return False
        if gte:
            return self.get_scm_is_ancestor(version)
        else:
            return self.get_scm_version() == version

    def parse_version(self, spec: str) -> {}:
        if ',' in spec:
            source, version = spec.split(",")
            version = version.strip()
            if len(version) != 0:
                return {"source": source.strip(), "version": version.strip()}

            return {"source": source, "version": "master"}

        return {"source": spec, "version": "master"}


def merge_specs(mainspec, new):
    for key, req in new.items():
        if key not in mainspec:
            mainspec[key] = req
        else:
            mainspec[key] = mainspec[key] + req


class Project(GitVersioned):
    """
        An Impera project
    """
    PROJECT_FILE = "project.yml"
    _project = None

    def __init__(self, path):
        """
            Initialize the project, this includes
             * Loading the project.yaml (into self._project_data)
             * Setting paths from project.yaml
             * Loading all modules in the module path (into self.modules)
            It does not include
             * verify if project.yml corresponds to the modules in self.modules

            @param path: The directory where the project is located

        """
        super().__init__(path)
        self.project_path = path

        if not os.path.exists(path):
            raise Exception("Unable to find project directory %s" % path)

        project_file = os.path.join(path, Project.PROJECT_FILE)

        if not os.path.exists(project_file):
            raise Exception(
                "Project directory does not contain a project file")

        with open(project_file, "r") as fd:
            self._project_data = yaml.load(fd)

        if "modulepath" not in self._project_data:
            raise Exception("modulepath is required in the project(.yml) file")

        modulepath = self._project_data["modulepath"]
        if not isinstance(modulepath, list):
            modulepath = [modulepath]
        self.modulepath = [os.path.abspath(os.path.join(path, x)) for x in modulepath]
        self.resolver = CompositeModuleRepo([makeRepo(x) for x in self.modulepath])

        if "repo" not in self._project_data:
            raise Exception("repo is required in the project(.yml) file")

        repo = self._project_data["repo"]
        self.repolist = [x for x in repo]
        self.externalResolver = CompositeModuleRepo([makeRepo(x) for x in self.repolist])

        self.downloadpath = None
        if "downloadpath" in self._project_data:
            self.downloadpath = os.path.abspath(os.path.join(
                path, self._project_data["downloadpath"]))

            if not os.path.exists(self.downloadpath):
                os.mkdir(self.downloadpath)

        self.freeze_file = os.path.join(path, "module.version")
        self._freeze_versions = self._load_freeze(self.freeze_file)

        self.virtualenv = env.VirtualEnv(os.path.join(path, "env"))
        self.reloadModules()

    @classmethod
    def get_project_dir(cls, cur_dir):
        """
            Find the project directory where we are working in. Traverse up until we find Project.PROJECT_FILE or reach /
        """
        project_file = os.path.join(cur_dir, Project.PROJECT_FILE)

        if os.path.exists(project_file):
            return cur_dir

        parent_dir = os.path.abspath(os.path.join(cur_dir, os.pardir))
        if parent_dir == cur_dir:
            raise ProjectNotFoundExcpetion("Unable to find an Impera project")

        return cls.get_project_dir(parent_dir)

    @classmethod
    def get(cls):
        """
            Get the instance of the project
        """
        if cls._project is None:
            cls._project = Project(cls.get_project_dir(os.curdir))

        return cls._project

    @classmethod
    def set(cls, project):
        """
            Get the instance of the project
        """
        cls._project = project
        plugins.PluginMeta.clear()

    def _load_freeze(self, freeze_file: str) -> {}:
        """
            Load the versions defined in the freeze file
        """
        if not os.path.exists(freeze_file):
            return {}

        with open(freeze_file, "r") as fd:
            return yaml.load(fd)

    def reloadModules(self):
        self.modules = self.discover(self.modulepath)

    def load_plugins(self) -> None:
        """
            Load all plug-ins
        """
        for module in self.modules.values():
            module.load_plugins()

    def discover(self, path: str) -> dict:
        """
            Discover and load configuration modules in the given path

            @param path: A list of paths to search for modules
        """
        module_dirs = {}
        # generate a module list and take precedence into account
        for module_dir in path:
            for sub_dir in glob.glob(os.path.join(module_dir, '*')):
                if Module.is_valid_module(sub_dir):
                    mod_name = os.path.basename(sub_dir)
                    module_dirs[mod_name] = sub_dir

        # create a list of modules
        modules = {}
        for name, path in module_dirs.items():
            mod = Module(self, path)
            modules[name] = mod
            if not mod.get_name() == name:
                raise InvalidModuleException(
                    "Directory %s expected to contain module %s but contains %s" % (path, name, mod.get_name()))

        return modules

    def verify(self) -> None:
        # verify module dependencies
        result = True
        result &= self.verify_requires(self.modules)
        for module in self.modules.values():
            result &= module.verify_requires(self.modules)

            if module._meta["name"] in self._freeze_versions:
                versioninfo = self._freeze_versions[module._meta["name"]]

                def shouldequal(one, field, thingname):
                    if field not in versioninfo:
                        return
                    other = versioninfo[field]
                    if one != other:
                        raise Exception("The installed %s (%s) of module %s, does not match the %s in the module file (%s)."
                                        % (thingname, one, module._meta["name"], thingname, other))

                shouldequal(str(module._meta["version"]), "version", "version")
                shouldequal(str(module.get_scm_url()), "repo", "repo url")
                shouldequal(str(module.get_scm_version()), "hash", "hash")
                shouldequal(str(module.get_scm_branch()), "branch", "branch")

        if not result:
            raise Exception("Not all module dependencies have been met.")

    def use_virtual_env(self) -> None:
        """
            Use the virtual environment
        """
        self.virtualenv.use_virtual_env()

    def requires(self) -> dict:
        """
            Return the requires of this project
        """
        req = {}
        if "requires" in self._project_data and self._project_data["requires"] is not None:
            for name, spec in self._project_data["requires"].items():
                req[name] = [x for x in parse_requirements(spec)]

        return req

    def sorted_modules(self) -> list:
        """
            Return a list of all modules, sorted on their name
        """
        names = self.modules.keys()
        names = sorted(names)

        mod_list = []
        for name in names:
            mod_list.append(self.modules[name])

        return mod_list

    def collect_requirements(self):
        """
            Collect the list of all requirements of all modules in the project.
        """
        all_reqs = set()

        for mod in self.modules.values():
            all_reqs.update(mod.get_requirements())

        return all_reqs

    def get_name(self):
        return "project.yml"

    name = property(get_name)


class Module(GitVersioned):
    """
        This class models an Impera configuration module
    """
    requires_fields = ["name", "license"]

    def __init__(self, project: Project, path: str, **kwmeta: dict):
        """
            Create a new configuration module

            :param project: A reference to the project this module belongs to.
            :param path: Where is the module stored
            :param kwmeta: Meta-data
        """
        super().__init__(path)
        self._project = project
        self._meta = kwmeta
        self._plugin_namespaces = []

        if not Module.is_valid_module(self._path):
            raise InvalidModuleException(("Module %s is not a valid Impera configuration module. Make sure that a " +
                                          "model/_init.cf file exists and a module.yml definition file.") % self._path)

        self.load_module_file()
        self.is_versioned()

    def get_name(self):
        """
            Returns the name of the module (if the meta data is set)
        """
        if "name" in self._meta:
            return self._meta["name"]

        return None

    name = property(get_name)

    def get_version(self):
        """
            Return the version of this module
        """
        if "version" in self._meta:
            return self._meta["version"]

        return None

    version = property(get_version)

    def _force_http(self, source_string):
        """
            Force the given string to http
        """
        new_source = source_string
        try:
            result = util.parse_url(source_string)
            if result.scheme is None:
                return new_source

            if result.scheme != "http" and result.scheme != "https":
                # try to convert it to an anonymous https url
                new_source = source_string.replace(result.scheme, "http")

        except exceptions.LocationParseError:
            # probably in git@host:repo format
            m = re.search("^(?P<user>[^@]+)@(?P<host>[^:]+):(?P<repo>.+)$", source_string)
            if m is not None:
                new_source = "http://%(user)s@%(host)s/%(repo)s" % m.groupdict()

        if new_source != source_string:
            LOGGER.info("Reformated source from %s to %s" % (source_string, new_source))

        return new_source

    def get_source(self) -> str:
        """
            Get the source url of this module. If git-http-only is true, we try to convert the all urls that are not valid
            http urls.
        """
        source = self._meta["source"]
        if not Config.getboolean("config", "git-http-only", False):
            return source

        return self._force_http(source)

    source = property(get_source)

    def requires(self) -> dict:
        """
            Get the requires for this module
        """
        if "requires" not in self._meta or self._meta["requires"] is None:
            return {}

        req = {}
        for name, spec in self._meta["requires"].items():
            req[name] = [x for x in parse_requirements(spec)]
        return req

    def is_versioned(self):
        """
            Check if this module is versioned, and if so the version number in the module file should
            have a tag. If the version has + the current revision can be a child otherwise the current
            version should match the tag
        """
        if not os.path.exists(os.path.join(self._path, ".git")):
            LOGGER.warning("Module %s is not version controlled, we recommend you do this as soon as possible."
                           % self._meta["name"])
            return False

#         if "version" in self._meta:
#             version_str = str(self._meta["version"])
#             version = StrictVersion(version_str)
#             higher = "a" in version_str or "b" in version_str
#
#             proc = subprocess.Popen(
#                 ["git", "show-ref", "--head"], cwd=self._path, stdout=subprocess.PIPE)
#             refs = {}
#             for line in proc.communicate()[0].decode().split("\n"):
#                 items = line.split(" ")
#                 if len(items) > 1:
#                     ref_id = items[0]
#                     ref = items[1]
#
#                     refs[ref] = ref_id
#
#             ref_spec = "refs/tags/%s" % version
#             if not higher:
#                 if ref_spec not in refs:
#                     LOGGER.warning(("Version %s defined in module %s is not available as tag. Use a or b followed by a number" +
#                                     " to indicate a pre release (i.e. 0.2b1 for dev of 0.2)") % (version, self._meta["name"]))
#                     return False
#
#                 else:
#                     # check that the id of HEAD matches the id of the version
#                     # tag
#                     if refs["HEAD"] != refs[ref_spec]:
#                         LOGGER.warning(("Module %s is set to version %s, but current revision (%s) does not match version " +
#                                         "tag (%s).") % (self._meta["name"], version, refs["HEAD"], refs[ref_spec]))
#                         return False
#
#             else:
#                 if ref_spec[:-1] in refs:
#                     LOGGER.warning(("Module %s defines this is a development version (a or b appended to version) of %s, but " +
#                                     "the release version is already available as tag.") % (self._meta["name"], str(version)))
#                     return False

        return True

    @classmethod
    def is_valid_module(cls, module_path):
        """
            Checks if this module is a valid configuration module. A module should contain a
            module.yml file.
        """
        if not os.path.isfile(os.path.join(module_path, "module.yml")):
            return False

        return True

    def load_module_file(self):
        """
            Load the imp module definition file
        """
        with open(os.path.join(self._path, "module.yml"), "r") as fd:
            mod_def = yaml.load(fd)

            if mod_def is None or len(mod_def) < len(Module.requires_fields):
                raise InvalidModuleFileException("The module file of %s does not have the required fields: %s" %
                                                 (self._path, ", ".join(Module.requires_fields)))

            for name, value in mod_def.items():
                self._meta[name] = value

        for req_field in Module.requires_fields:
            if req_field not in self._meta:
                raise InvalidModuleFileException(
                    "%s is required in module file of module %s" % (req_field, self._path))

        if self._meta["name"] != os.path.basename(self._path):
            LOGGER.warning("The name in the module file (%s) does not match the directory name (%s)"
                           % (self._meta["name"], os.path.basename(self._path)))

    def get_module_files(self):
        """
            Returns the path of all model files in this module, relative to the module root
        """
        files = []
        for model_file in glob.glob(os.path.join(self._path, "model", "*.cf")):
            files.append(model_file)

        return files

    def load_plugins(self):
        """
            Load all plug-ins from a configuration module
        """
        plugin_dir = os.path.join(self._path, "plugins")

        if not os.path.exists(plugin_dir):
            return

        if not os.path.exists(os.path.join(plugin_dir, "__init__.py")):
            raise Exception(
                "The plugin directory %s should be a valid python package with a __init__.py file" % plugin_dir)

        try:
            mod_name = self._meta["name"]
            imp.load_package("impera_plugins." + mod_name, plugin_dir)

            self._plugin_namespaces.append(mod_name)

            for py_file in glob.glob(os.path.join(plugin_dir, "*.py")):
                if not py_file.endswith("__init__.py"):
                    # name of the python module
                    sub_mod = "impera_plugins." + mod_name + "." + os.path.basename(py_file).split(".")[0]
                    self._plugin_namespaces.append(sub_mod)

                    # load the python file
                    imp.load_source(sub_mod, py_file)

        except ImportError:
            LOGGER.exception(
                "Unable to load all plug-ins for module %s" % self._meta["name"])

    def update(self):
        """
            Update the module by doing a git pull
        """
        sys.stdout.write("Updating %s " % self._meta["name"])
        sys.stdout.flush()

        output = self._call(["git", "pull"], self._path, "git pull")

        if output is not None:
            sys.stdout.write("branches ")
            sys.stdout.flush()

        output = self._call(
            ["git", "pull", "--tags"], self._path, "git pull --tags")

        if output is not None:
            sys.stdout.write("tags ")
            sys.stdout.flush()

        print("done")

    def install(self, modulepath):
        """
            Install this module if it has not been installed yet, and install its dependencies.
        """
        if not os.path.exists(self._path):
            # check if source and version are available
            if "source" not in self._meta or "version" not in self._meta:
                raise Exception(
                    "Source and version are required to install a configuration module.")

            LOGGER.info(
                "Cloning module %s from %s", self._meta["name"], self.source)
            cmd = ["git", "clone", self.source, self._meta["name"]]
            output = self._call(cmd, modulepath, "git clone")

            if output is None:
                new_source = self._force_http(self.source)
                LOGGER.info(
                    "Cloning module %s from %s", self._meta["name"], new_source)
                cmd = ["git", "clone", new_source, self._meta["name"]]
                output = self._call(cmd, modulepath, "git clone")

                if output is None:
                    LOGGER.critical("Unable to get module %s" %
                                    self._meta["name"])
                    return None

        # reload the module
        module = Module(self._project, self._path)

        return module

    def checkout_version(self, version: Version):
        """
            Checkout the given version
        """
        # versions = self.versions()

        # if version in versions:
        #    print(version)
        raise NotImplementedError()

    def checkout_branch(self, branch):
        """
            Checkout the given branch
        """

        self._call(["git", "checkout", branch], self._path, "git checkout ")

    def versions(self):
        """
            Provide a list of all versions available in the repository
        """
        output = self._call(
            ["git", "show-ref", "--head"], self._path, "git qshow-ref")
        lines = output.decode().split("\n")

        version_list = []
        for line in lines:
            obj = re.search(
                "^(?P<hash>[a-f0-9]{40}) refs/tags/(?P<version>.+)$", line)

            if obj:
                try:
                    version_list.append(StrictVersion(obj.group("version")))
                except Exception:
                    pass

        return version_list

    def _call(self, cmd: list, path: str, cmd_name: str) -> str:
        proc = subprocess.Popen(
            cmd, cwd=path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            output = proc.communicate(timeout=60)
        except TimeoutExpired:
            print("Unable to %(cmd_name)s module %(name)s, %(cmd_name)s timed out" %
                  {"name": self._meta["name"], "cmd_name": cmd_name})

            return None

        if proc.returncode is None or proc.returncode > 0:
            print("")
            print("Unable to %(cmd_name)s %(name)s, %(cmd_name)s provided this output:" %
                  {"name": self._meta["name"], "cmd_name": cmd_name})
            print(output[0].decode())
            print(output[1].decode())

            return None

        return output[0]

    def status(self):
        """
            Run a git status on this module
        """
        cmd = ["git", "status", "--porcelain"]
        output = self._call(cmd, self._path, "git status").decode()

        files = [x.strip() for x in output.split("\n") if x != ""]

        if len(files) > 0:
            print("Module %s (%s)" % (self._meta["name"], self._path))
            for f in files:
                print("\t%s" % f)

            print()

    def push(self):
        """
            Run a git status on this module
        """
        sys.stdout.write("%s (%s) " % (self._meta["name"], self._path))
        sys.stdout.flush()

        cmd = ["git", "push", "--porcelain"]
        output = self._call(cmd, self._path, "git push")
        if output is not None:
            sys.stdout.write("branches ")
            sys.stdout.flush()

        cmd = ["git", "push", "--porcelain", "--tags"]
        output = self._call(cmd, self._path, "git push tags")
        if output is not None:
            sys.stdout.write("tags ")
            sys.stdout.flush()

        print("done")

    def get_python_requirements(self):
        """
            Install python requirements with pip in a virtual environment
        """
        file = os.path.join(self._path, "requirements.txt")
        if os.path.exists(file):
            with open(file, 'r') as fd:
                return fd.read()
        else:
            return None

    def get_requirements(self):
        """
            Returns an array of requirements of this module
        """
        if not os.path.exists(os.path.join(self._path, "requirements.txt")):
            return set()

        with open(os.path.join(self._path, "requirements.txt"), "r") as fd:
            return set([l.strip() for l in fd.readlines()])


class ModuleTool(object):
    """
        A tool to manage configuration modules
    """

    def __init__(self):
        self._mod_handled_list = set()

    def execute(self, cmd, args):
        """
            Execute the given command
        """
        if hasattr(self, cmd):
            method = getattr(self, cmd)
            method(*args)

        else:
            raise Exception("%s not implemented" % cmd)

    def help(self):
        """
            Show a list of commands
        """
        print("Available commands: list")

    def list(self):
        """
            List all modules in a table
        """
        table = []
        name_length = len("Name") + 5
        version_length = 7
        names = sorted(Project.get().modules.keys())
        for name in names:
            mod = Project.get().modules[name]
            if "version" in mod._meta:
                version = str(mod._meta["version"])
                table.append((name, version))

                if len(name) > name_length:
                    name_length = len(name)

                if len(version) > version_length:
                    version_length = len(version)
            else:
                print(
                    "Module %s does not contain a version, invalid module" % name)

        print("+" + "-" * (name_length + version_length + 5) + "+")
        print("| Name%s | Version%s |" % (
            " " * (name_length - len("Name")), " " * (version_length - len("Version"))))
        print("+" + "-" * (name_length + version_length + 5) + "+")
        for name, version in table:
            print("| %s | %s |" % (name + " " * (name_length - len(name)),
                                   version + " " * (version_length - len(version))))

        print("+" + "-" * (name_length + version_length + 5) + "+")

    def update(self):
        """
            Update all modules from their source
        """
        for mod in Project.get().sorted_modules():
            mod.update()

    def _install(self, project, modulename, requirements):
        """
            Do a recursive install
        """
        # verify pressence in module path
        path = project.resolver.path_for(modulename)
        if path is not None:
            # if exists, report
            LOGGER.info("module %s already found at %s", modulename, path)
            gitprovider.fetch(path)
        else:
            # otherwise install
            path = os.path.join(project.downloadpath, modulename)
            result = project.externalResolver.clone(modulename, project.downloadpath)
            if not result:
                raise InvalidModuleException("could not locat module with name: %s", modulename)

        versions = gitprovider.get_all_tags(path)

        def try_parse(x):
            try:
                return parse_version(x)
            except:
                return None

        versions = [x for x in [try_parse(v) for v in versions] if x is not None]
        versions = sorted(versions, reverse=True)

        for r in requirements:
            versions = [x for x in r.specifier.filter(versions)]

        if len(versions) == 0:
            print("no suitable version found for module %s" % modulename)
        else:
            gitprovider.checkout_tag(path, str(versions[0]))

        return Module(project, path)

    def install(self, project=Project.get()):
        """
            Install all modules the project requires
        """
        specs = project.requires().copy()
        worklist = []
        worklist.extend(specs.keys())
        modules = {}

        while len(worklist) != 0:
            work = worklist.pop(0)
            LOGGER.info("requesting install for: %s", work)
            module = self._install(project, work, specs[work])
            modules[work] = module
            reqs = module.requires()
            merge_specs(specs, reqs)
            for name in reqs.keys():
                if name not in modules:
                    worklist.append(name)

        # verify if installed versions are consistent with all rules
        for name, spec in specs.items():
            module = modules[name]
            version = parse_version(str(module.version))
            for r in spec:
                if version not in r:
                    LOGGER.warning("requirement %s on module %s not fullfilled, not at version %s" % (r, name, version))

        # do python install
        pyreq = [x.strip() for x in [module.get_python_requirements() for module in modules.values()] if x is not None]
        pyreq = '\n'.join(pyreq).split("\n")

        project.virtualenv.install_from_list(pyreq)

        project.reloadModules()

    def status(self):
        """
            Run a git status on all modules and report
        """
        for mod in Project.get().sorted_modules():
            mod.status()

    def push(self):
        """
            Push all modules
        """
        for mod in Project.get().sorted_modules():
            mod.push()

    def freeze(self, create_file=True):
        """
            Freeze the version of all modules
        """
        project = Project.get()
        if os.path.exists(project.freeze_file) and create_file:
            print(
                "A module.version file already exists, overwrite this file? y/n")
            while True:
                value = sys.stdin.readline().strip()
                if value != "y" and value != "n":
                    print("Please answer with y or n")
                else:
                    if value == "n":
                        return

                    break

        file_content = {}

        for mod in Project.get().sorted_modules():
            version = str(mod.get_version())
            modc = {'version': version}

            repo = mod.get_scm_url()
            tag = mod.get_scm_version()

            if repo is not None:
                modc["repo"] = repo
                modc["hash"] = tag

            branch = mod.get_scm_branch()

            if branch is not None:
                modc["branch"] = branch

            file_content[mod._meta["name"]] = modc

        if create_file:
            with open(project.freeze_file, "w+") as fd:
                fd.write(yaml.dump(file_content))

        return file_content

    def verify(self):
        """
            Verify dependencies and frozen module versions
        """
        Project.get().verify()

    def commit(self, version=None):
        """
            Commit all current changes.
        """
        subprocess.call(["git", "commit", "-a"])

    def validate(self, options=""):
        """
            Validate the module we are currently in
        """
        parse_only = "-s" in options
        valid = True
        module = Module(None, os.path.realpath(os.curdir))
        LOGGER.info("Successfully loaded module %s with version %s" % (module.name, module.version))

        if not module.is_versioned():
            LOGGER.error("Module is not versioned correctly, validation will fail")
            valid = False

        # compile the source files in the module
        ns_root = Namespace("__root__")
        ns_mod = Namespace(module.name, ns_root)
        for model_file in module.get_module_files():
            try:
                ns = ns_mod
                if not model_file.endswith("_init.cf"):
                    part_name = model_file.split("/")[-1][:-3]
                    ns = Namespace(part_name, ns_mod)

                parse(ns, model_file)
                LOGGER.info("Successfully parsed %s" % model_file)
            except Exception:
                valid = False
                LOGGER.exception("Unable to parse %s, validation will fail" % model_file)

        if parse_only:
            if not valid:
                sys.exit(1)
            sys.exit(0)
        # create a test project
        LOGGER.info("Creating a new project to test the module")
        project_dir = tempfile.mkdtemp()
        try:
            lib_dir = os.path.join(project_dir, "libs")
            os.mkdir(lib_dir)

            LOGGER.info("Cloning %s module" % module.name)
            proc = subprocess.Popen(
                ["git", "clone", module._path], cwd=lib_dir)
            proc.wait()

            LOGGER.info("Setting up project")
            with open(os.path.join(project_dir, "project.yml"), "w+") as fd:
                fd.write("""name: test
description: Project to validate module %(name)s
modulepath: libs
downloadpath: libs
requires:
    %(name)s: %(source)s, "%(version)s"
""" % {"name": module.name, "version": module.get_scm_version(), "source": module._path})

            LOGGER.info("Installing dependencies")
            test_project = Project(project_dir)
            test_project.use_virtual_env()
            Project.set(test_project)
            self.install()

            LOGGER.info("Compiling empty initial model")
            main_cf = os.path.join(project_dir, "main.cf")
            with open(main_cf, "w+") as fd:
                fd.write("")

            project = Project(project_dir)
            Project._project = project
            LOGGER.info("Verifying module set")
            project.verify()
            LOGGER.info("Loading all plugins")
            project.load_plugins()

            values = impera.compiler.do_compile()

            if values is not None:
                LOGGER.info("Successfully compiled module and its dependencies.")
            else:
                LOGGER.error("Unable to compile module and its dependencies, validation will fail")
                valid = False

        finally:
            if options == "noclean":
                LOGGER.info("Project not cleanded, root at %s", project_dir)

            else:
                shutil.rmtree(project_dir)

        if not valid:
            sys.exit(1)

        sys.exit(0)
