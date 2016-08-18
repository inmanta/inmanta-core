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
import urllib
import os
import base64

from inmanta.agent.handler import provider, ResourceHandler
from inmanta.execute.util import Unknown
from inmanta.resources import Resource, resource, ResourceNotFoundExcpetion
from inmanta import methods


LOGGER = logging.getLogger(__name__)
FILE_SOURCE = "imp-module-source:"


def store_file(exporter, obj):
    content = obj.content
    if isinstance(content, Unknown):
        return content

    elif content.startswith(FILE_SOURCE):
        parts = urllib.parse.urlparse(content[len(FILE_SOURCE):])

        if parts.scheme == "file":
            with open(parts.path, "rb") as fd:
                content = fd.read()

        elif parts.scheme == "tmp":
            with open(parts.path, "rb") as fd:
                content = fd.read()

        else:
            raise Exception("%s scheme not support for file %s" %
                            (parts.scheme, parts.path))

    return exporter.upload_file(content)


@resource("std::Service", agent="host.name", id_attribute="name")
class Service(Resource):
    """
        This class represents a service on a system.
    """
    fields = ("onboot", "state", "name")


@resource("std::File", agent="host.name", id_attribute="path")
class File(Resource):
    """
        A file on a filesystem
    """
    fields = ("path", "owner", "hash", "group", "permissions", "purged", "reload")
    map = {"hash": store_file, "permissions": lambda y, x: int(x.mode)}


@resource("std::Directory", agent="host.name", id_attribute="path")
class Directory(Resource):
    """
        A directory on a filesystem
    """
    fields = ("path", "owner", "group", "permissions", "purged", "reload")
    map = {"permissions": lambda y, x: int(x.mode)}


@resource("std::Package", agent="host.name", id_attribute="name")
class Package(Resource):
    """
        A software package installed on an operating system.
    """
    fields = ("name", "state", "reload")


@resource("std::Symlink", agent="host.name", id_attribute="target")
class Symlink(Resource):
    """
        A symbolic link on the filesystem
    """
    fields = ("source", "target", "purged", "reload")


@provider("std::File", name="posix_file")
class PosixFileProvider(ResourceHandler):
    """
        This handler can deploy files on a unix system
    """
    def check_resource(self, resource):
        current = resource.clone(purged=False, reload=resource.reload, hash=0)
        if not self._io.file_exists(resource.path):
            current.purged = True
            current.hash = 0
        else:
            current.hash = self._io.hash_file(resource.path)

            # upload the previous version for back up and for generating a diff!
            content = self._io.read_binary(resource.path)

            if not self.stat_file(current.hash):
                self.upload_file(current.hash, content)

            for key, value in self._io.file_stat(resource.path).items():
                setattr(current, key, value)

        return current

    def _list_changes(self, desired):
        current = self.check_resource(desired)
        changes = self._diff(current, desired)

        if desired.purged:
            if current.purged:
                return {}

            else:
                return {"purged": (False, True)}

        return changes

    def list_changes(self, desired):
        changes = self._list_changes(desired)
        return changes

    def do_changes(self, resource):
        changes = self._list_changes(resource)
        changed = False

        if "purged" in changes and changes["purged"][1]:
            self._io.remove(resource.path)
            return True

        if "hash" in changes:
            # write the new version
            dir_name = os.path.dirname(resource.path)

            if self._io.file_exists(dir_name):
                data = self.get_file(resource.hash)
                self._io.put(resource.path, data)
                changed = True
            else:
                raise Exception("Parent of %s does not exist, unable to write file." % resource.path)

        if "permissions" in changes or ("purged" in changes and changes["purged"][0]):
            if not self._io.file_exists(resource.path):
                raise Exception("Cannot change permissions of %s because does not exist" % resource.path)

            self._io.chmod(resource.path, str(resource.permissions))
            changed = True

        if "owner" in changes or "group" in changes or ("purged" in changes and changes["purged"][0]):
            if not self._io.file_exists(resource.path):
                raise Exception("Cannot change ownership of %s because does not exist" % resource.path)

            self._io.chown(resource.path, resource.owner, resource.group)
            changed = True

        return changes

    def snapshot(self, resource):
        return self._io.read_binary(resource.path)


@provider("std::Service", name="systemd")
class SystemdService(ResourceHandler):
    """
        A handler for services on systems that use systemd
    """
    def available(self, resource):
        return self._io.file_exists("/usr/bin/systemctl")

    def check_resource(self, resource):
        current = resource.clone()

        exists = self._io.run("/usr/bin/systemctl", ["status", "%s.service" % resource.name])[0]

        if re.search('Loaded: error', exists):
            raise ResourceNotFoundExcpetion("The %s service does not exist" % resource.name)

        running = self._io.run("/usr/bin/systemctl",
                               ["is-active", "%s.service" % resource.name])[2] == 0
        enabled = self._io.run("/usr/bin/systemctl",
                               ["is-enabled", "%s.service" % resource.name])[2] == 0

        if running:
            current.state = "running"
        else:
            current.state = "stopped"

        current.onboot = enabled
        return current

    def list_changes(self, desired):
        current = self.check_resource(desired)
        changes = self._diff(current, desired)
        return changes

    def can_reload(self):
        """
            Can this handler reload?
        """
        return True

    def do_reload(self, resource):
        """
            Reload this resource
        """
        self._io.run("/usr/bin/systemctl", ["reload-or-restart", "%s.service" % resource.name])

    def do_changes(self, resource):
        changes = self.list_changes(resource)
        changed = False

        if "state" in changes and changes["state"][0] != changes["state"][1]:
            action = "start"
            if changes["state"][1] == "stopped":
                action = "stop"

            # start or stop the service
            result = self._io.run("/usr/bin/systemctl", [action, "%s.service" % resource.name])

            if re.search("^Failed", result[1]):
                raise Exception("Unable to %s %s: %s" % (action, resource.name, result[1]))

            changed = True

        if "onboot" in changes and changes["onboot"][0] != changes["onboot"][1]:
            action = "enable"

            if not changes["onboot"][1]:
                action = "disable"

            result = self._io.run("/usr/bin/systemctl", [action, "%s.service" % resource.name])
            changed = True

            if re.search("^Failed", result[1]):
                raise Exception("Unable to %s %s: %s" % (action, resource.name, result[1]))

        return changed


@provider("std::Service", name="redhat_service")
class ServiceService(ResourceHandler):
    """
        A handler for services on systems that use service
    """
    def available(self, resource):
        return (self._io.file_exists("/sbin/chkconfig") and self._io.file_exists("/sbin/service") and
                not self._io.file_exists("/usr/bin/systemctl"))

    def check_resource(self, resource):
        current = resource.clone()
        exists = self._io.run("/sbin/chkconfig", ["--list", resource.name])[0]

        if re.search('error reading information on service', exists):
            raise ResourceNotFoundExcpetion("The %s service does not exist" % resource.name)

        enabled = ":on" in self._io.run("/sbin/chkconfig", ["--list", resource.name])[0]
        running = self._io.run("/sbin/service", [resource.name, "status"])[2] == 0

        current.enabled = enabled
        if running:
            current.state = "running"
        else:
            current.state = "stopped"

        return current

    def list_changes(self, desired):
        current = self.check_resource(desired)
        changes = self._diff(current, desired)
        return changes

    def can_reload(self):
        """
            Can this handler reload?
        """
        return True

    def do_reload(self, resource):
        """
            Reload this resource
        """
        self._io.run("/sbin/service", [resource.name, "reload"])

    def do_changes(self, resource):
        changes = self.list_changes(resource)
        changed = False

        if "state" in changes and changes["state"][0] != changes["state"][1]:
            action = "start"
            if changes["state"][1] == "stopped":
                action = "stop"

            # start or stop the service
            result = self._io.run("/sbin/service", [resource.name, action])

            if re.search("^Failed", result[1]):
                raise Exception("Unable to %s %s: %s" % (action, resource.name, result[1]))

            changed = True

        if "enabled" in changes and changes["enabled"][0] != changes["enabled"][1]:
            action = "on"

            if not changes["enabled"][1]:
                action = "off"

            result = self._io.run("/sbin/chkconfig", [resource.name, action])
            changed = True

            if re.search("^Failed", result[1]):
                raise Exception("Unable to %s %s: %s" % (action, resource.name, result[1]))

        return changed


@provider("std::Package", name="yum")
class YumPackage(ResourceHandler):
    """
        A Package handler that uses yum
    """
    def available(self, resource):
        return (self._io.file_exists("/usr/bin/rpm") or self._io.file_exists("/bin/rpm")) \
            and (self._io.file_exists("/usr/bin/yum") or self._io.file_exists("/usr/bin/dnf"))

    def _parse_fields(self, lines):
        props = {}
        key = ""
        old_key = None
        for line in lines:
            if line.strip() == "":
                continue

            if line.strip() == "Available Packages":
                break

            result = re.search("^(.+) :\s+(.+)", line)
            if result is None:
                continue

            key, value = result.groups()
            key = key.strip()

            if key == "":
                props[old_key] += " " + value
            else:
                props[key] = value
                old_key = key

        return props

    def _run_yum(self, args):
        #todo: cache value
        if self._io.file_exists("/usr/bin/dnf"):
            return self._io.run("/usr/bin/dnf", ["-d", "0", "-e", "0", "-y"] + args)
        else:
            return self._io.run("/usr/bin/yum", ["-d", "0", "-e", "0", "-y"] + args)

    def check_resource(self, resource):
        yum_output = self._run_yum(["info", resource.name])
        lines = yum_output[0].split("\n")

        output = self._parse_fields(lines[1:])

        if "Repo" not in output:
            return {"state": "removed"}

        state = "removed"

        if output["Repo"] == "installed" or output["Repo"] == "@System":
            state = "installed"

        # check if there is an update
        yum_output = self._run_yum(["check-update", resource.name])
        lines = yum_output[0].split("\n")

        data = {"state": state, "version": output["Version"],
                "release": output["Release"], "update": None}

        if len(lines) > 0:
            parts = re.search("([^\s]+)\s+([^\s]+)\s+([^\s]+)", lines[0])
            if parts is not None and not lines[0].startswith("Security:"):
                version_str = parts.groups()[1]
                version, release = version_str.split("-")

                data["update"] = (version, release)

        return data

    def list_changes(self, resource):
        state = self.check_resource(resource)

        changes = {}
        if resource.state == "removed":
            if state["state"] != "removed":
                changes["state"] = (state["state"], resource.state)

        elif resource.state == "installed" or resource.state == "latest":
            if state["state"] != "installed":
                changes["state"] = (state["state"], "installed")

        if "update" in state and state["update"] is not None and resource.state == "latest":
            changes["version"] = ((state["version"], state["release"]), state["update"])

        return changes

    def _result(self, output):
        stdout = output[0].strip()
        error_msg = output[1].strip()
        if output[2] != 0:
            raise Exception("Yum failed: stdout:"+stdout +" errout: " + error_msg)

    def do_changes(self, resource):
        changes = self.list_changes(resource)
        changed = False

        if "state" in changes:
            if changes["state"][1] == "removed":
                self._result(self._run_yum(["remove", resource.name]))

            elif changes["state"][1] == "installed":
                self._result(self._run_yum(["install", resource.name]))
                changed = True

        if "version" in changes:
            self._result(self._run_yum(["update", resource.name]))
            changed = True

        return changed


@provider("std::Directory", name="posix_directory")
class DirectoryHandler(ResourceHandler):
    """
        A handler for creating directories

        TODO: add recursive operations
    """
    def check_resource(self, resource):
        current = resource.clone(purged=False)

        if not self._io.file_exists(resource.path):
            current.purged = True

        else:
            for key, value in self._io.file_stat(resource.path).items():
                setattr(current, key, value)

        return current

    def list_changes(self, resource):
        current = self.check_resource(resource)
        if resource.purged:
            if current.purged:
                return {}

            else:
                return {"purged": (False, True)}

        changes = self._diff(current, resource)
        return changes

    def do_changes(self, resource):
        changes = self.list_changes(resource)

        changed = False
        if "purged" in changes:
            if changes["purged"][1]:
                self._io.rmdir(resource.path)
                return
            else:
                self._io.mkdir(resource.path)

        if "permissions" in changes or ("purged" in changes and changes["purged"][0]):
            mode = str(resource.permissions)
            self._io.chmod(resource.path, mode)
            changed = True

        if "owner" in changes or "group" in changes or ("purged" in changes and changes["purged"][0]):
            self._io.chown(resource.path, resource.owner, resource.group)
            changed = True

        return changed


@provider("std::Symlink", name="posix_symlink")
class SymlinkProvider(ResourceHandler):
    """
        This handler can deploy symlinks on unix systems
    """
    def available(self, resource):
        return self._io.file_exists("/usr/bin/ln") or self._io.file_exists("/bin/ln")

    def check_resource(self, resource):
        current = resource.clone(purged=False)

        if not self._io.file_exists(resource.target):
            current.purged = True

        elif not self._io.is_symlink(resource.target):
            raise Exception("The target of resource %s already exists but is not a symlink." % resource)

        else:
            current.source = self._io.readlink(resource.target)

        return current

    def list_changes(self, resource):
        current = self.check_resource(resource)

        changes = {}

        if resource.purged:
            if current.purged:
                return {}

            else:
                changes["purged"] = (False, True)
                return changes

        if current.purged:
            changes["source"] = (None, resource.source)
            changes["target"] = (None, resource.target)

        elif current.source != resource.source:
            changes["source"] = (current.source, resource.source)
            changes["target"] = (resource.target, resource.target)

        return changes

    def do_changes(self, resource):
        changes = self.list_changes(resource)
        changed = False

        if "purged" in changes:
            if changes["purged"][1]:
                self._io.remove(resource.path)
                changed = True
                return changed

            else:
                self._io.symlink(changes["source"][1], changes["target"][1])
                changed = True

        if "source" in changes:
            self._io.symlink(changes["source"][1], changes["target"][1])
            changed = True

        return changed

