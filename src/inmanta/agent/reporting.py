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
from typing import TYPE_CHECKING, Callable, Union

if TYPE_CHECKING:
    from inmanta.protocol.endpoints import SessionEndpoint

try:
    import resource
except ImportError:
    resource = None

LOGGER = logging.getLogger(__name__)

ReportReturn = Union[dict[str, list[str]], dict[str, str], dict[str, float], str]
reports: dict[str, Callable[["SessionEndpoint"], ReportReturn]] = {}


def collect_report(agent: "SessionEndpoint") -> dict[str, ReportReturn]:
    out = {}
    for name, report in reports.items():
        try:
            out[name] = report(agent)
        except Exception:
            out[name] = "ERROR"
            LOGGER.exception("could generate report for entry: %s" % name)

    return out


def report_environment(agent: "SessionEndpoint") -> str:
    return str(agent._env_id)


reports["environment"] = report_environment


def report_platform(agent: "SessionEndpoint") -> str:
    value = platform.platform()
    if value is None:
        return "unknown"
    return value


reports["platform"] = report_platform


def report_hostname(agent: "SessionEndpoint") -> str:
    return platform.node()


reports["hostname"] = report_hostname


def report_python(agent: "SessionEndpoint") -> str:
    return f"{platform.python_implementation()} {platform.python_version()} {platform.python_build()}"


reports["python"] = report_python


def report_pid(agent: "SessionEndpoint") -> str:
    return str(os.getpid())


reports["pid"] = report_pid


def report_resources(agent: "SessionEndpoint") -> dict[str, float]:
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
