********************
Define API endpoints
********************

This page describes how to add an API endpoint to the Inmanta server. Adding a new API endpoint requires two methods: an
API method and an API handle. The API method provides the specification of the endpoint. This includes the HTTP request
method, the path to the endpoint, etc. The API handle on the other hand provides the actual implementation of the endpoint.

API Method
##########

The Python function that acts as an API method should be annotated using the ``method`` decorator. The implementation of the
method should be left empty.

An example is shown in the code snippet below.

.. code-block:: python

    import uuid
    from inmanta.const import ClientType
    from inmanta.protocol.decorators import method

    @method(path="/project/<id>", operation="GET", client_types=[ClientType.api])
    def get_project(id: uuid.UUID):
        """
            Get a project and a list of the ids of all environments.

            :param id: The id of the project to retrieve.
            :return: The project and a list of environment ids.
            :raises NotFound: The project with the given id doesn't exist.
        """

This API method defines an HTTP GET operation at the path ``/project/<id>`` which can be used by a client of type api (cli,
web-console and 3rd party service). The id parameter in the path will be passed to the associate API handle. A docstring can be
associated with the API method. This information will be included in the OpenAPI documentation, available
via the ``/docs`` endpoint of the Inmanta server.

A complete list of all the arguments accepted by the ``method`` decorator is given below.

.. automethod:: inmanta.protocol.decorators.method


API Handle
##########

An API handle function should be annotated with the ``handle`` decorator and should contain all the arguments of the
associated API method and the parameters defined in the path of the endpoint. The names these arguments can be mapped onto a
different name by passing arguments to the ``handle`` decorator.

An example is shown in the code snippet below.

.. code-block:: python

    import uuid
    from inmanta.server import protocol
    from inmanta.types import Apireturn
    from inmanta import data
    from inmanta.protocol import methods

    @protocol.handle(methods.get_project, project_id="id")
    async def get_project(self, project_id: uuid.UUID) -> Apireturn:
        try:
            project = await data.Project.get_by_id(project_id)
            environments = await data.Environment.get_list(project=project_id)

            if project is None:
                return 404, {"message": "The project with given id does not exist."}

            project_dict = project.to_dict()
            project_dict["environments"] = [e.id for e in environments]

            return 200, {"project": project_dict}
        except ValueError:
            return 404, {"message": "The project with given id does not exist."}

        return 500

The first argument of the ``handle`` decorator defines that this is the handle function for the ``get_project`` API method.
The second argument remaps the ``id`` argument of the API method to the ``project_id`` argument in the handle function.

The arguments and the return type of the handle method can be any built-in Python type or a user-defined object. The input
format of an API call be verified automatically using Pydantic.

An overview of all the arguments of the ``handle`` decorator are shown below.

.. autoclass:: inmanta.protocol.decorators.handle
