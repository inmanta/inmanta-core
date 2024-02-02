1 - refactor to work with dict repr
2 - move

                          -  pass the info regarding the resource (cannot use self)
                        v
    async def _execute(self, ctx: handler.HandlerContext, requires: dict[ResourceIdStr, const.ResourceState]) -> None:
        """
        :param ctx: The context to use during execution of this deploy
        :param requires: A dictionary that maps each dependency of the resource to be deployed, to its latest resource
                         state that was not `deploying'.
        """
        ctx.debug("Start deploy %(deploy_id)s of resource %(resource_id)s", deploy_id=self.gid, resource_id=self.resource_id)


into a new ABC executor -> to be able to both use current implementation and future schedulor.get_executor()


3 - investigate into the ctx object (creation place / where it is used / logging aspects )

4 - code loading be able to delegate to future process mgmr
