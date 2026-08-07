from inmanta.agent.handler import ResourceHandler, provider


@provider("std::testing::NullResource", name="myhandler")
class MyHandler(ResourceHandler):
    pass
