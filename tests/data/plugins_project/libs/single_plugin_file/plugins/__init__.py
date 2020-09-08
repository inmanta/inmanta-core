from inmanta.agent.handler import ResourceHandler, provider


@provider("std::File", name="myhandler")
class MyHandler(ResourceHandler):
    pass
