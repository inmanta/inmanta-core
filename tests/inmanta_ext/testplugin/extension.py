from builtins import super

from typing import List

from inmanta.server import SLICE_SERVER, SLICE_AGENT_MANAGER
from inmanta.server.extensions import ApplicationContext
from inmanta.server.protocol import ServerSlice


class TestSlice(ServerSlice):
    def __init__(self):
        super(TestSlice, self).__init__("testplugin.testslice")

    def get_dependencies(self) -> List[str]:
        return [SLICE_SERVER, SLICE_AGENT_MANAGER]


def setup(application: ApplicationContext) -> None:
    application.register_slice(TestSlice())
