from inmanta.agent.handler import ResourceHandler, provider
from inmanta_plugins.multiple_plugin_files.helpers import helper


@provider("multiple_plugin_files::NullResourceBis", name="myhandler")
class MyHandler(ResourceHandler):
    pass
