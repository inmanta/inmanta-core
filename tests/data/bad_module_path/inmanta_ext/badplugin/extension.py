
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_SERVER
from inmanta.server.extensions import ApplicationContext
from inmanta.server.protocol import ServerSlice


class MyTestSlice(ServerSlice):
    def __init__(self):
        super().__init__("badplugin.badslice")

    def get_dependencies(self) -> list[str]:
        return [SLICE_SERVER, SLICE_AGENT_MANAGER]

    async def start(self) -> None:
        raise Exception("Too bad, this plugin is broken")


def setup(application: ApplicationContext) -> None:
    application.register_slice(MyTestSlice())
