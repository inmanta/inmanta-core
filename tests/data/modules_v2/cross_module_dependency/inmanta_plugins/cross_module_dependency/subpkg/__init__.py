

import logging

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel("DEBUG")


LOGGER.debug("MODULE IS BEING LOADED")

# TODO remove above

from inmanta.plugins import plugin
@plugin("subpkg_plugin")
def subpkg_plugin(message: "string"):
    print(message)

