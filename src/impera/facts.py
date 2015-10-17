"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@impera.io
"""
import logging


from impera import protocol
from impera.config import Config
from impera.execute.util import Unknown
from impera.export import Exporter, Offline, unknown_parameters
from impera.stats import Stats

LOGGER = logging.getLogger(__name__)


def get_fact(res, fact_name: str, default_value=None) -> "any":
    """
        Get the fact with the given name from the database
    """
    resource_id = Exporter.get_id(res)

    fact_value = None
    if Config.getboolean("config", "offline", False):
        fact_value = Offline.get().get_fact(resource_id, fact_name, Unknown(source=res))

    else:
        try:
            client = protocol.Client("compiler", "client")

            env = Config.get("config", "environment", None)
            if env is None:
                raise Exception("The environment of this model should be configured in config>environment")

            result = client.get_param(tid=env, id=fact_name, resource_id=resource_id)

            if result.code == 200:
                fact_value = result.result["value"]
            else:
                LOGGER.debug("Param %s of resource %s is unknown", fact_name, resource_id)
                fact_value = Unknown(source=res)
                unknown_parameters.append({"resource": resource_id, "parameter": fact_name, "source": "fact"})
        except ConnectionRefusedError:
            fact_value = Unknown(source=res)
            unknown_parameters.append({"resource": resource_id, "parameter": fact_name, "source": "fact"})

    if isinstance(fact_value, Unknown) and default_value is not None:
        return default_value

    Stats.get("get fact").increment()
    return fact_value
