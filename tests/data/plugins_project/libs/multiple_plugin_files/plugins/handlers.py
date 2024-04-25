from inmanta.agent.handler import ResourceHandler, provider
from inmanta_plugins.multiple_plugin_files.helpers import helper


@provider("std::testing::NullResource", name="myhandler")
class MyHandler(ResourceHandler):
    pass
