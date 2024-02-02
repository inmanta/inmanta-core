import asyncio
from abc import ABC
import logging
from typing import Optional, Any

from inmanta import const
from inmanta.agent import handler
from inmanta.agent.handler import HandlerAPI, SkipResource
from inmanta.agent.io.remote import ChannelClosedException
from inmanta.data import ResourceIdStr

POC_ON = True
LOGGER = logging.getLogger(__name__)

#class Executor(ABC):
#    @staticmethod
#    async def execute(ra, ctx: handler.HandlerContext, requires: dict[ResourceIdStr, const.ResourceState]) -> None:
#        """
#        :param ctx: The context to use during execution of this deploy
#        :param requires: A dictionary that maps each dependency of the resource to be deployed, to its latest resource
#                         state that was not `deploying'.
#        """
#        ctx.debug("Start deploy %(deploy_id)s of resource %(resource_id)s", deploy_id=ra.gid, resource_id=ra.resource_id)
#        # setup provider
#        provider: Optional[HandlerAPI[Any]] = None
#        try:
#            if not POC_ON:
#                provider = await ra.scheduler.agent.get_provider(ra.resource)
#            else:
#                provider = scheduler.get_executor_for(ra.ve)
#        except ChannelClosedException as e:
#            ctx.set_status(const.ResourceState.unavailable)
#            ctx.exception(str(e))
#            return
#        except Exception:
#            ctx.set_status(const.ResourceState.unavailable)
#            ctx.exception("Unable to find a handler for %(resource_id)s", resource_id=ra.resource.id.resource_version_str())
#            return
#        else:
#            # main execution
#            try:
#                await asyncio.get_running_loop().run_in_executor(
#                    ra.scheduler.agent.thread_pool,
#                    provider.deploy,
#                    ctx,
#                    ra.resource,
#                    requires,
#                )
#                if ctx.status is None:
#                    ctx.set_status(const.ResourceState.deployed)
#            except ChannelClosedException as e:
#                ctx.set_status(const.ResourceState.failed)
#                ctx.exception(str(e))
#            except SkipResource as e:
#                ctx.set_status(const.ResourceState.skipped)
#                ctx.warning(msg="Resource %(resource_id)s was skipped: %(reason)s", resource_id=ra.resource.id, reason=e.args)
#            except Exception as e:
#                ctx.set_status(const.ResourceState.failed)
#                ctx.exception(
#                    "An error occurred during deployment of %(resource_id)s (exception: %(exception)s",
#                    resource_id=ra.resource.id,
#                    exception=repr(e),
#                )
#        finally:
#            if provider is not None:
#                provider.close()
#
#class PocExecutor(Executor):
#    async def execute(self):
#        LOGGER.info("PocExecutor executing...")
#
#
#class ResourceActionBasedExecutor(Executor):
#
#
#
#class Scheduler():
#    def request_resources_loading(self, version: int, resources: dict[str, dict[str, object]]):
#        """
#        :param resources: dict representation of the resource (serialized form)
#        :param logger: TBD
#        """
#        LOGGER.info("Request to load resources %s %s" % version, resources)
#
#    def get_executor_for(self, version, resource) -> Executor:
#        if POC_ON:
#            return PocExecutor()
#        return ResourceActionBasedExecutor()
#
#
#scheduler = Scheduler()
#
#
#
