from inmanta.agent.executor import MPManager


async def test_executor_server():
    manager = MPManager()
    manager._init_once()

    child1 = await manager.make_child_and_connect("Testchild")

    result = await child1.connection.call("echo", ["aaaa"])

    assert ["aaaa"] == result

    print("stopping")
    await manager.stop()
    print("joining")
    await manager.join(10)
    print("done")

    # assert child1.connection.transport.is_closing()
