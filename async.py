import asyncio
import contextvars
import time
from asyncio import Future, Task
from typing import Awaitable, Coroutine

from inmanta.execute.proxy import DynamicProxy
from inmanta.execute.runtime import ResultVariable, Waiter


class AwaitableProxy(DynamicProxy, Future, Waiter):
    def __init__(self, instance: ResultVariable):
        DynamicProxy.__init__(self, instance)
        Future.__init__(self)
        self.waiting = False

    def __await__(self):
        out = super().__await__()
        if not object.__getattribute__(self, "waiting"):
            print("Start waiting across the loop")
            self._get_instance().waitfor(self)
        return out

    def __setattr__(self, attribute: str, value: object) -> None:
        # override from DynamicProxy, didn't sink time in cleanup
        object.__setattr__(self, attribute, value)

    def ready(self, other) -> None:
        self.set_result(self._get_instance().get_value())
        self.waiting = True


async def myplugin(variable: AwaitableProxy) -> object:
    async def actual_io() -> None:
        async def non_blocking_async_function() -> None:
            print("executing non_blocking_async_function")
            future: Future = asyncio.get_running_loop().create_future()
            future.set_result(42)
            return await future
        # normal sleep
        await asyncio.sleep(0.1)
        print("non-blocking sleep -> should see scheduler yielding control multiple times in a row")
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        # normal sleep
        await asyncio.sleep(0.1)
        print("non-blocking function call -> should see scheduler yielding control multiple times in a row")
        await non_blocking_async_function()
        await non_blocking_async_function()
        await non_blocking_async_function()
        await non_blocking_async_function()

    print("Plugin start: some actual async IO")
    await actual_io()
    print("Plugin waiting for variable")
    result = await variable
    print("Plugin fetched variable: %s" % result)
    return result


# Simplified, nothing added
class QueueScheduler:
    def __init__(self) -> None:
        self.allwaiters = set()

    def add_to_all(self, item: Waiter) -> None:
        self.allwaiters.add(item)

    def remove_from_all(self, item: Waiter) -> None:
        self.allwaiters.remove(item)


class PluginWaiter(Waiter, Awaitable):
    """
    Wait for a future to finish, then set a ResultVariable. PoC: might need to be restructured a bit to better resemble
    existing waiters.
    """

    def __init__(self, queue: QueueScheduler, result: ResultVariable, function: Coroutine) -> None:
        super().__init__(queue)
        self.result = result
        self.task = asyncio.create_task(function)
        self.task.add_done_callback(lambda task: self.ready())

    def ready(self) -> None:
        print("PluginWaiter ready")
        self.result.set_value(self.task.result(), location=None)
        self.queue.remove_from_all(self)

    def __await__(self):
        return self.task.__await__()


class PluginAstNode:
    def __init__(self, plugin: Coroutine) -> None:
        self.plugin = plugin

    # simplified: assuming no other requires
    def requires_emit(self, queue_scheduler: QueueScheduler) -> dict:
        temp = ResultVariable()
        # asyncio waiting logic converted to our internal waiting logic
        PluginWaiter(queue_scheduler, temp, self.plugin)
        return {self: temp}

    def execute(self, requires: dict) -> None:
        return requires[self].value


scheduler_context_var = contextvars.ContextVar("inmanta_scheduler")


async def schedule() -> None:
    event_loop = asyncio.get_running_loop()

    queue: QueueScheduler = QueueScheduler()

    variable: ResultVariable = ResultVariable()
    proxy: AwaitableProxy = AwaitableProxy(variable)

    ast_node: PluginAstNode = PluginAstNode(myplugin(proxy))
    requires = ast_node.requires_emit(queue)

    max_iterations: int = 1000
    for i in range(max_iterations):
        # mock normal queue handling
        if i == 100:
            # mock assign statement execution
            variable.set_value(42, location=None)
        else:
            # mock other statement execution
            print(i)
            time.sleep(0.01)

        async def exhaust_event_loop():
            scheduler_context_var.set(True)
            await asyncio.sleep(0)
            while event_loop.async_progress:
                # as long as the async event loop keeps making progress, keep yielding control
                print("more progress possible: yielding once more")
                await asyncio.sleep(0)
            scheduler_context_var.set(False)

        await exhaust_event_loop()

        if not queue.allwaiters:
            break
    assert not queue.allwaiters
    # mock execution, in practice this would be done by yet another Waiter (didn't model this because it is trivial)
    print("execute: %s" % ast_node.execute(requires))


class CustomEventLoop(asyncio.DefaultEventLoopPolicy._loop_factory):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.async_progress: bool = False

    def call_soon(self, callback, *args, context=None):
        # Tasks that are awaiting a blocking call are rescheduled through a done_callback, call_soon is only called when a Task
        # can progress in any way: https://github.com/python/cpython/blob/079ea445706e2afae8f1bcc53fe967b0839b310c/Lib/asyncio/tasks.py#L269
        # => keep track of whether the latest callback was done by the scheduler's yield logic -> if something else comes in,
        # more progression is possible on this event loop
        if context is None or not context.get(scheduler_context_var, False):
            self.async_progress = True
        else:
            self.async_progress = False

        return super().call_soon(callback, *args, context=context)

class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    _loop_factory = CustomEventLoop


asyncio.set_event_loop_policy(CustomEventLoopPolicy())
asyncio.run(schedule())
