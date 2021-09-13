"""
    Copyright 2017 Inmanta

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
import os
import platform
from typing import TYPE_CHECKING, Callable, Dict, List, Union

if TYPE_CHECKING:
    from inmanta.agent.agent import Agent

try:
    import resource
except ImportError:
    resource = None

LOGGER = logging.getLogger(__name__)

ReportReturn = Union[Dict[str, List[str]], Dict[str, str], Dict[str, float], str]
reports: Dict[str, Callable[["Agent"], ReportReturn]] = {}


def collect_report(agent: "Agent") -> Dict[str, ReportReturn]:
    out = {}
    for name, report in reports.items():
        try:
            out[name] = report(agent)
        except Exception:
            out[name] = "ERROR"
            LOGGER.exception("could generate report for entry: %s" % name)

    return out


def report_environment(agent: "Agent") -> str:
    return str(agent._env_id)


reports["environment"] = report_environment


def report_platform(agent: "Agent") -> str:
    value = platform.platform()
    if value is None:
        return "unknown"
    return value


reports["platform"] = report_platform


def report_hostname(agent: "Agent") -> str:
    return platform.node()


reports["hostname"] = report_hostname


def report_ips(agent: "Agent") -> Union[str, Dict[str, List[str]]]:
    try:
        import netifaces

        alladdresses = [netifaces.ifaddresses(i) for i in netifaces.interfaces()]
        v4 = [str(y["addr"]) for x in alladdresses if netifaces.AF_INET in x for y in x[netifaces.AF_INET]]
        v6 = [str(y["addr"]) for x in alladdresses if netifaces.AF_INET6 in x for y in x[netifaces.AF_INET6]]
        out = {"v4": v4, "v6": v6}
        return out
    except ImportError:
        import socket

        return socket.gethostbyname(socket.gethostname())


reports["ips"] = report_ips


def report_python(agent: "Agent") -> str:
    return "%s %s %s" % (platform.python_implementation(), platform.python_version(), platform.python_build())


reports["python"] = report_python


def report_pid(agent: "Agent") -> str:
    return str(os.getpid())


reports["pid"] = report_pid


def report_resources(agent: "Agent") -> Dict[str, float]:
    if resource is None:
        return {}

    ru = resource.getrusage(resource.RUSAGE_SELF)
    out = {
        "utime": ru.ru_utime,
        "stime": ru.ru_stime,
        "maxrss": ru.ru_maxrss,
        "ixrss": ru.ru_ixrss,
        "idrss": ru.ru_idrss,
        "isrss": ru.ru_isrss,
        "minflt": ru.ru_minflt,
        "majflt": ru.ru_majflt,
        "nswap": ru.ru_nswap,
        "inblock": ru.ru_inblock,
        "oublock": ru.ru_oublock,
        "msgsnd": ru.ru_msgsnd,
        "msgrcv": ru.ru_msgrcv,
        "nsignals": ru.ru_nsignals,
        "nvcsw": ru.ru_nvcsw,
        "nivcsw": ru.ru_nivcsw,
    }
    return out


reports["resources"] = report_resources
