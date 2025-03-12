import logging
from inmanta.agent.handler import PythonLogger
from inmanta.plugins import plugin
from inmanta.references import Reference

@plugin
def resolve(one: str | Reference[str]) -> str:
    if isinstance(one, Reference):
        # Construct a logger based on a python logger
        logger = PythonLogger(logging.getLogger("testing.resolver"))
        return one.resolve(logger)
    return one
