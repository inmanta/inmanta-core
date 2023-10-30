from inmanta.agent.handler import ResourceHandler, provider


@provider("std::Directory", name="myhandler")
class MyHandler(ResourceHandler):
    pass
