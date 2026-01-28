"""
Copyright 2025 Inmanta
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
Contact: code@inmanta.com
"""

import base64
import dataclasses
import re
import typing
import uuid
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Sequence, cast

import inmanta.data.sqlalchemy as models
import strawberry
from inmanta import data
from inmanta.data import get_session, get_session_factory, model
from inmanta.deploy import state
from inmanta.server.services.compilerservice import CompilerService
from sqlakeyset import Marker, unserialize_bookmark
from sqlakeyset.asyncio import select_page
from sqlalchemy import Boolean, Select, UnaryExpression, and_, asc, case, desc, func, not_, select
from strawberry import relay, scalars
from strawberry.schema.config import StrawberryConfig
from strawberry.types import Info
from strawberry.types.info import ContextType
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyLoader, StrawberrySQLAlchemyMapper

"""
The strawberry models in this file are mapped from the sqlalchemy models in inmanta.data.sqlalchemy.models.
We use a `StrawberrySQLAlchemyMapper` to map a sqlalchemy model to a strawberry model via the `type` decorator.

There are 4 important building blocks that we have to take into account:
    1) The strawberry class itself i.e.
        ```
            @mapper.type(models.Environment)
            class Environment:
                __exclude__ = [
                    "project_",
                    "agentprocess",
                    ...
                ]
                is_expert_mode: bool = strawberry.field(resolver=get_expert_mode)
                is_compiling: bool = strawberry.field(resolver=get_is_compiling)
        ```
         It is always decorated with `@mapper.type(<respective_sqlalchemy_model>)`
         We use the `__exclude__` attribute to exclude any attributes or relationships from the SQLAlchemy model that
         we don't want to expose via GraphQL
         It is also possible to add custom fields that only appear on this view that we want to expose to our user.
         We then add a custom resolver that fetches the correct value for these fields.

    2) The attributes of the `Query` class i.e.
        ```
            @strawberry.field
            async def environments(
                self,
                info: CustomInfo,
                first: typing.Optional[int] = strawberry.UNSET,
                after: typing.Optional[str] = strawberry.UNSET,
                last: typing.Optional[int] = strawberry.UNSET,
                before: typing.Optional[str] = strawberry.UNSET,
                filter: typing.Optional[EnvironmentFilter] = strawberry.UNSET,
                order_by: typing.Optional[Sequence[EnvironmentOrder]] = strawberry.UNSET,
            ) -> relay.ListConnection[Environment]:
                stmt = select(models.Environment)
                stmt = add_filter_and_sort(stmt, EnvironmentOrder.default_order(), filter, order_by)
                return await get_connection(
                    stmt, info=info, model="Environment", first=first, after=after, last=last, before=before
                )
        ```

        The `first`/`last`/`before`/`after` query arguments are used for pagination.
        It is possible to add custom parameters to the query that we want to use on resolution, like `filter` and `order_by`.
        We call `get_connection` to manually fetch the correct results and page information and return it to the user.

        If you don't exclude a certain relation from the model i.e. `project`
        you would then have to create a strawberry model for it.
        The strawberry-sqlalchemy-mapper (mapper for short) library
        will generate the `Connection` class for it as well in runtime.

    3) The `StrawberryFilter` child class for our strawberry model i.e.
        ```
            @strawberry.input
            class EnvironmentFilter(StrawberryFilter):
                id: typing.Optional[str] = strawberry.UNSET
        ```
        This class determines what fields we allow our users to filter on and what type we expect to receive.

        We can also define custom filters to handle more complex behaviour than simple equality.
        i.e. a filter to get values based on a list of enum values
        ```
            @strawberry.input
            class EnumFilter[T: StrEnum](CustomFilter):
                # Expects to receive a StrEnum.
                # Provides equal and not equal filters. Multiple enum values can be provided to include/exclude
                eq: list[T] | None = strawberry.UNSET
                neq: list[T] | None = strawberry.UNSET

                def apply_filter(self, stmt: Select[typing.Any], model: type[models.Base], key: str) -> Select[typing.Any]:
                    # Enums are stored as a string of their name in the database and not of their value
                    if self.eq is not None and self.eq is not strawberry.UNSET:
                        stmt = stmt.where(getattr(model, key).in_([x.name for x in self.eq]))
                    if self.neq is not None and self.neq is not strawberry.UNSET:
                        stmt = stmt.where(not_(getattr(model, key).in_([x.name for x in self.neq])))
                    return stmt
        ```
    4) The `StrawberryOrder` child class for our strawberry model i.e.
        ```
            @strawberry.input
            class EnvironmentOrder(StrawberryOrder):
                @property
                def model(self) -> type[models.Base]:
                    return models.Environment

                @property
                def key_to_model(self) -> dict[str, type[models.Base]]:
                    return {"id": self.model, "name": self.model}
        ```
        This class determines what fields we allow our users to sort the results.

    Some tips:
        - Use stmt.compile(compile_kwargs={"literal_binds": True}) to get the underlying SQL code of a statement.

    Known limitations:
        - No paging/filtering/sorting on nested relationships:
            https://github.com/strawberry-graphql/strawberry-sqlalchemy/issues/236
        - Limited relationship (or secondary) table support i.e. resourceaction_resource:
            https://github.com/strawberry-graphql/strawberry-sqlalchemy/issues/220

    Useful documentation:
        - Strawberry documentation:
            https://strawberry.rocks/docs
        - Strawberry-sqlalchemy-mapper documentation:
            https://github.com/strawberry-graphql/strawberry-sqlalchemy
        - Info on the relay spec for pagination:
            https://relay.dev/docs/guides/graphql-server-specification/
        - How strawberry implements relay:
            https://strawberry.rocks/docs/guides/pagination/connections#implementing-the-relay-connection-specification
        - Tool to visualize the GraphQL introspection schema:
            https://graphql-kit.com/graphql-voyager/
"""

mapper: StrawberrySQLAlchemyMapper[typing.Any] = StrawberrySQLAlchemyMapper()
DEFAULT_PER_PAGE: int = 50


def to_snake_case(name: str) -> str:
    """
    Convert a string from camelCase to snake_case.
    Strawberry converts the query, filter and order fields to camelCase.
    With this we accommodate the user to also filter and order in camelCase.
    """
    if re.match(r"[A-Z]", name):
        raise Exception("name cannot start with capital letter.")
    return re.sub("([A-Z])", r"_\1", name).lower()


@dataclasses.dataclass
class GraphQLContext:
    """
    Context passed down by the GraphQL slice, to be used by the Strawberry models.
    """

    compiler_service: CompilerService


class CustomFilter(ABC):
    """
    Base class for custom filters.
    Subclasses are expected to implement apply_filter with the concrete logic of the filter
    """

    @abstractmethod
    def apply_filter(self, stmt: Select[typing.Any], model: type[models.Base], key: str) -> Select[typing.Any]:
        """
        Applies the logic of this custom filter to the given statement.
        """
        pass


@strawberry.input
class EnumFilter[T: StrEnum](CustomFilter):
    """
    Expects to receive a StrEnum.
    Provides equal and not equal filters. Multiple enum values can be provided to include/exclude
    """

    eq: list[T] | None = strawberry.UNSET
    neq: list[T] | None = strawberry.UNSET

    def apply_filter(self, stmt: Select[typing.Any], model: type[models.Base], key: str) -> Select[typing.Any]:
        # Enums are stored as a string of their name in the database and not of their value
        if self.eq is not None and self.eq is not strawberry.UNSET:
            stmt = stmt.where(getattr(model, key).in_([x.name for x in self.eq]))
        if self.neq is not None and self.neq is not strawberry.UNSET:
            stmt = stmt.where(not_(getattr(model, key).in_([x.name for x in self.neq])))
        return stmt


@strawberry.input
class StrFilter(CustomFilter):
    """
    Provides equal/not equal/contains/not contains filters.
    Multiple values can be provided to each filter and multiple filters can be active at the same time.
    contains/not contains support wild card matching with `_` or `%`
    """

    eq: list[str] | None = strawberry.UNSET
    neq: list[str] | None = strawberry.UNSET
    contains: list[str] | None = strawberry.UNSET
    not_contains: list[str] | None = strawberry.UNSET

    def apply_filter(self, stmt: Select[typing.Any], model: type[models.Base], key: str) -> Select[typing.Any]:
        if self.eq is not None and self.eq is not strawberry.UNSET:
            stmt = stmt.where(getattr(model, key).in_(self.eq))
        if self.neq is not None and self.neq is not strawberry.UNSET:
            stmt = stmt.where(not_(getattr(model, key).in_(self.neq)))
        if self.contains is not None and self.contains is not strawberry.UNSET:
            for c in self.contains:
                stmt = stmt.where(getattr(model, key).ilike(c))
        if self.not_contains is not None and self.not_contains is not strawberry.UNSET:
            for c in self.not_contains:
                stmt = stmt.where(not_(getattr(model, key).ilike(c)))
        return stmt


class StrawberryFilter:
    """
    This class determines what fields we allow our users to filter on.
    We then apply these fields with the `add_filter_and_sort` function.
    The `@strawberry.input` decorator is necessary for this class to be allowed as a parameter of a query.
    """

    def get_filter_dict(self) -> dict[str, typing.Any]:
        """
        Returns the filter in dict form.
        This is fed to the SQLAlchemy query to apply as filter.
        This is only used for simple filters i.e. exact match on the same table
        """
        return {key: value for key, value in self.__dict__.items()}

    def apply_filters(self, stmt: Select[typing.Any]) -> Select[typing.Any]:
        """
        Applies the filters to the given query.
        """
        return stmt.filter_by(**self.get_filter_dict())

    @property
    def get_models_to_join(self) -> set[type[models.Base]]:
        """
        When filtering or sorting on values in a different table, it is necessary to manually do the join.
        This function returns the tables to join if necessary.
        """
        return set()


@strawberry.input
class StrawberryOrder:
    """
    This class determines what fields we allow our users to sort the results on.
    The sorting is applied with the `add_filter_and_sort` function.
    The `@strawberry.input` decorator is necessary for this class to be allowed as a parameter of a query

    :param key: The key to sort on.
    :param order: `asc` or `desc` to determine if we are sorting in ascending or descending order.
    """

    key: str
    order: str = "asc"

    @classmethod
    def default_order(cls) -> dict[str, UnaryExpression[typing.Any]]:
        """
        The default order of this strawberry class.
        Required for each subclass of StrawberryOrder.
        Necessary for paging with sqlakeyset.
        """
        raise NotImplementedError()

    @property
    def model(self) -> type[models.Base]:
        """
        The base model of the query. To be overridden by subclasses.
        """
        return models.Base

    @property
    def key_to_model(self) -> dict[str, type[models.Base]]:
        """
        The allowed keys and respective model to sort on.
        """
        return {}

    def get_order_by(self) -> UnaryExpression[typing.Any]:
        """
        Returns an Expression to use while sorting.
        """
        snake_case_key = to_snake_case(self.key)
        if snake_case_key not in self.key_to_model.keys():
            raise Exception(
                f"Invalid sort key provided expected one of {self.key_to_model.keys()} instead got {snake_case_key}."
            )
        if self.order == "asc":
            return asc(getattr(self.key_to_model[snake_case_key], snake_case_key))
        elif self.order == "desc":
            return desc(getattr(self.key_to_model[snake_case_key], snake_case_key))
        raise Exception(f"Invalid sort order provided expected asc or desc, got {self.order}.")


def get_expert_mode(root: "Environment") -> bool:
    """
    Checks settings of environment to figure out if expert mode is enabled or not
    """
    assert hasattr(root, "settings")  # Make mypy happy
    assert isinstance(root.settings, dict)
    if "enable_lsm_expert_mode" not in root.settings["settings"]:
        return False
    return cast(bool, root.settings["settings"]["enable_lsm_expert_mode"]["value"])


def get_is_compiling(root: "Environment", info: strawberry.Info) -> bool:
    """
    Checks compiler service to figure out if environment is compiling or not
    """
    compiler_service = info.context.get("compiler_service", None)
    assert isinstance(compiler_service, CompilerService)
    assert hasattr(root, "id")  # Make mypy happy
    return compiler_service.is_environment_compiling(environment_id=root.id)


def get_settings(root: "Environment") -> scalars.JSON:
    """
    Returns all environment settings (the ones set by the user and default values for the ones that are not)
    and their definitions.

    Strawberry is a bit finicky with its return types, it can't handle a dict return type we have to cast it as scalars.JSON.
    root.settings is of type scalars.JSON, and scalars.JSON is defined as an object
    so we have to do some assertions on it to make mypy happy.
    """
    assert hasattr(root, "settings")
    assert isinstance(root.settings, dict)
    modified_settings = root.settings["settings"]
    assert modified_settings is not None
    setting_values: dict[str, model.EnvironmentSettingDetails] = {}
    for key, setting_info in data.Environment._settings.items():
        if stored_setting := modified_settings.get(key, None):
            setting_values[key] = model.EnvironmentSettingDetails(
                value=stored_setting["value"],
                protected=stored_setting.get("protected", False),
                protected_by=stored_setting.get("protected_by", None),
            )
        else:
            default_value = setting_info.default
            assert default_value is not None  # Should never happen but setting_info.default is Optional
            setting_values[key] = model.EnvironmentSettingDetails(value=default_value)
    setting_definitions = dict(sorted(data.Environment.get_setting_definitions_for_api(setting_values).items()))
    return scalars.JSON({"settings": setting_values, "definition": setting_definitions})


@mapper.type(models.Environment)
class Environment:
    # Add every relation/attribute that we don't want to expose in our GraphQL endpoint to `__exclude__`
    __exclude__ = [
        "project_",
        "agentprocess",
        "code",
        "compile",
        "configurationmodel",
        "discoveredresource",
        "environmentmetricsgauge",
        "environmentmetricstimer",
        "notification",
        "parameter",
        "resource_persistent_state",
        "unknownparameter",
        "agent",
        "inmanta_module",
        "resource_set",
        "resource_set_configuration_model",
        "role_assignment",
        "settings",
    ]
    is_expert_mode: bool = strawberry.field(resolver=get_expert_mode)
    is_compiling: bool = strawberry.field(resolver=get_is_compiling)
    settings: scalars.JSON = strawberry.field(resolver=get_settings)


@strawberry.input
class EnvironmentFilter(StrawberryFilter):
    id: typing.Optional[str] = strawberry.UNSET


@strawberry.input
class EnvironmentOrder(StrawberryOrder):

    @classmethod
    def default_order(cls) -> dict[str, UnaryExpression[typing.Any]]:
        return {"id": asc(models.Environment.id)}

    @property
    def model(self) -> type[models.Base]:
        return models.Environment

    @property
    def key_to_model(self) -> dict[str, type[models.Base]]:
        return {"id": self.model, "name": self.model}


@mapper.type(models.Notification)
class Notification:
    __exclude__ = ["environment_", "compile"]


@strawberry.input
class NotificationFilter(StrawberryFilter):
    environment: uuid.UUID
    cleared: typing.Optional[bool] = strawberry.UNSET


class NotificationOrder(StrawberryOrder):
    @classmethod
    def default_order(cls) -> dict[str, UnaryExpression[typing.Any]]:
        return {"environment": asc(models.Notification.environment), "id": asc(models.Notification.id)}

    @property
    def model(self) -> type[models.Base]:
        return models.Notification

    @property
    def key_to_model(self) -> dict[str, type[models.Base]]:
        return {"created": self.model}


def get_requires_length(root: "Resource") -> int:
    """
    Checks the length of the requires of the resource
    """
    assert hasattr(root, "attributes")  # Make mypy happy
    return len(root.attributes.get("requires", []))


def get_purged(root: "Resource") -> bool:
    """
    Checks the length of the requires of the resource
    """
    assert hasattr(root, "attributes")  # Make mypy happy
    return bool(root.attributes.get("purged"))


@mapper.type(models.Resource)
class Resource:
    __exclude__ = ["resource_set_"]
    requires_length: int = strawberry.field(resolver=get_requires_length)
    purged: bool = strawberry.field(resolver=get_purged)


@strawberry.input
class ResourceFilter(StrawberryFilter):
    environment: uuid.UUID
    resource_type: StrFilter | None = strawberry.UNSET
    resource_id_value: StrFilter | None = strawberry.UNSET
    agent: StrFilter | None = strawberry.UNSET
    purged: bool | None = strawberry.UNSET
    blocked: EnumFilter[state.Blocked] | None = strawberry.UNSET
    compliance_state: EnumFilter[state.Compliance] | None = strawberry.UNSET
    last_handler_run: EnumFilter[state.HandlerResult] | None = strawberry.UNSET
    is_deploying: bool | None = strawberry.UNSET
    is_orphan: bool | None = strawberry.UNSET

    @property
    def model(self) -> type[models.Base]:
        return models.Resource

    @property
    def rps_model(self) -> type[models.Base]:
        return models.ResourcePersistentState

    @property
    def get_models_to_join(self) -> set[type[models.Base]]:
        rps_join = ["blocked", "compliance_state", "last_handler_run", "is_deploying", "is_orphan"]
        for attr in rps_join:
            if getattr(self, attr) is not strawberry.UNSET:
                return {self.rps_model}
        return set()

    def apply_filters(self, stmt: Select[typing.Any]) -> Select[typing.Any]:
        # Every filter we apply to the resource is custom, so we don't use `get_filter_dict`
        key_to_model = {
            "resource_type": self.model,
            "resource_id_value": self.model,
            "agent": self.model,
            "blocked": self.rps_model,
            "compliance_state": self.rps_model,
            "last_handler_run": self.rps_model,
        }
        for key, model in key_to_model.items():
            attr = getattr(self, key)
            if attr is not None and attr is not strawberry.UNSET:
                stmt = attr.apply_filter(stmt, model, key)
        if self.purged is not None and self.purged is not strawberry.UNSET:
            stmt = stmt.filter(models.Resource.attributes["purged"].astext.cast(Boolean).is_(self.purged))
        if self.is_deploying is not None and self.is_deploying is not strawberry.UNSET:
            stmt = stmt.filter(models.ResourcePersistentState.is_deploying == self.is_deploying)
        if self.is_orphan is not None and self.is_orphan is not strawberry.UNSET:
            stmt = stmt.filter(models.ResourcePersistentState.is_orphan == self.is_orphan)
        return stmt


class ResourceOrder(StrawberryOrder):

    @classmethod
    def default_order(cls) -> dict[str, UnaryExpression[typing.Any]]:
        return {
            "environment": asc(models.Resource.environment),
            "resource_set": asc(models.Resource.resource_set),
            "resource_id": asc(models.Resource.resource_id),
        }

    @property
    def model(self) -> type[models.Base]:
        return models.Resource

    @property
    def rps_model(self) -> type[models.Base]:
        return models.ResourcePersistentState

    @property
    def key_to_model(self) -> dict[str, type[models.Base]]:
        return {
            "agent": self.model,
            "resource_type": self.model,
            "resource_id_value": self.model,
            "blocked": self.rps_model,
            "compliance_state": self.rps_model,
            "last_handler_run": self.rps_model,
            "is_deploying": self.rps_model,
        }


@mapper.type(models.ResourcePersistentState)
class ResourcePersistentState:
    __tablename__ = "resource_persistent_state"
    __exclude__ = ["resource_set_"]


def add_filter_and_sort(
    stmt: Select[typing.Any],
    default_sorting: dict[str, UnaryExpression[typing.Any]],
    filter: typing.Optional[StrawberryFilter] = strawberry.UNSET,
    order_by: typing.Optional[Sequence[StrawberryOrder]] = strawberry.UNSET,
) -> Select[typing.Any]:
    """
    Adds filter and sorting to the given statement.
    """
    if filter is not None and filter is not strawberry.UNSET:
        stmt = filter.apply_filters(stmt)
    order_expressions: dict[str, UnaryExpression[typing.Any]] = {}
    if order_by is not None and order_by is not strawberry.UNSET:
        for order in order_by:
            if order.key in order_expressions:
                raise Exception(f"Sorting key appears multiple times in orderBy: {order.key}")
            order_expressions[order.key] = order.get_order_by()
    for default_key, order_expression in default_sorting.items():
        if default_key not in order_expressions:
            order_expressions[default_key] = order_expression
    stmt = stmt.order_by(*order_expressions.values())
    return stmt


def do_required_resource_joins(
    stmt: Select[typing.Any],
    filter: typing.Optional[StrawberryFilter] = strawberry.UNSET,
    order_by: typing.Optional[Sequence[StrawberryOrder]] = strawberry.UNSET,
) -> Select[typing.Any]:
    """
    Checks the given filter and order_by to see if we need to join any external tables.
    Only working for the Resource table
    """
    models_to_join: set[type[models.Base]] = set()
    if order_by is not None and order_by is not strawberry.UNSET:
        models_to_join = models_to_join | {
            o.key_to_model[to_snake_case(o.key)] for o in order_by if o.key_to_model[to_snake_case(o.key)] != o.model
        }
    if filter is not None and filter is not strawberry.UNSET:
        models_to_join = models_to_join | filter.get_models_to_join
    if models.ResourcePersistentState in models_to_join:
        stmt = stmt.join(
            models.ResourcePersistentState,
            and_(
                models.Resource.resource_id == models.ResourcePersistentState.resource_id,
                models.Resource.environment == models.ResourcePersistentState.environment,
            ),
        )
    return stmt


def encode_cursor(cursor: str) -> str:
    """
    :param cursor: The cursor received from sqlakeyset without direction information ('<'/'>').
    :return: The base64 encoded cursor in str form.
    """
    return base64.b64encode(f"{relay.types.PREFIX}:{cursor}".encode()).decode()


def decode_cursor(cursor: str) -> str:
    """
    :param cursor: The cursor received as an argument from the user in base64.
        Expected in the format that Edge.resolve_edge returns (prefixed with `relay.types.PREFIX:`).
    :return: The decoded cursor in str form.
    """
    decoded_cursor = base64.b64decode(cursor.encode()).decode()
    prefix = f"{relay.types.PREFIX}:"
    if prefix not in decoded_cursor:
        raise Exception(f"Invalid cursor provided: {cursor}")
    return decoded_cursor.split(prefix)[1]


async def get_connection(
    stmt: Select[typing.Any],
    model: str,
    info: Info,
    first: typing.Optional[int] = strawberry.UNSET,
    after: typing.Optional[str] = strawberry.UNSET,
    last: typing.Optional[int] = strawberry.UNSET,
    before: typing.Optional[str] = strawberry.UNSET,
) -> relay.ListConnection[typing.Any]:
    """
    Build the connection object. Here we do all the pagination and fetching of results (edges) to return to the user.
    We do not call `ListConnection.resolve_connection` because:
     1) We already got the PageInfo arguments from sqlakeyset
     2) It calls `Edge.resolve_edge` with a cursor that is not useful to us
    """
    async with get_session() as session:
        per_page: int
        # Get results per page and sanitation of input arguments
        if first is not None and first is not strawberry.UNSET:
            if (last is not None and last is not strawberry.UNSET) or (before is not None and before is not strawberry.UNSET):
                raise Exception("`first` is not allowed in conjunction with `last` or `before`")
            per_page = first
        elif last is not None and last is not strawberry.UNSET:
            if (after is not None and after is not strawberry.UNSET) or (before is None or before is strawberry.UNSET):
                raise Exception("`last` is only allowed in conjunction with `before`")
            per_page = last
        else:
            per_page = DEFAULT_PER_PAGE

        # Get cursor and direction of results to fetch (forwards/backwards)
        page: Marker | None = None
        if after is not None and after is not strawberry.UNSET:
            if before is not None and before is not strawberry.UNSET:
                raise Exception("`after` is not allowed in conjunction with `before`")
            page = unserialize_bookmark(f">{decode_cursor(after)}")
        elif before is not None and before is not strawberry.UNSET:
            page = unserialize_bookmark(f"<{decode_cursor(before)}")

        # Fetch the page using sqlakeyset
        result = await select_page(session, stmt, per_page=per_page, page=page)
        edges = []
        # We use the private methods for the mapper because their respective public attributes like `mapper.connection_types`
        # Are only filled when the private methods are called first. The private methods use the public attributes as cache so
        # it is fine to call them repeatedly
        connection = cast(relay.ListConnection, mapper._connection_type_for(model))
        for cursor, value in result.paging.bookmark_items():
            formatted_cursor = str(cursor)[1:]
            sqla_obj = next(iter(value._mapping.values()))
            edge = cast(relay.Edge, mapper._edge_type_for(model))
            node = connection.resolve_node(sqla_obj, info=info)
            edges.append(edge.resolve_edge(cursor=formatted_cursor, node=node))

        return connection(
            edges=edges,
            page_info=strawberry.relay.PageInfo(
                has_next_page=result.paging.has_next,
                has_previous_page=result.paging.has_previous,
                start_cursor=encode_cursor(result.paging.bookmark_previous[1:]),
                end_cursor=encode_cursor(result.paging.bookmark_next[1:]),
            ),
        )


def get_schema(context: GraphQLContext) -> strawberry.Schema:
    """
    Initializes the Strawberry GraphQL schema.
    It is initiated in a function instead of being declared at the module level, because we have to do this
    after the SQLAlchemy engine is initialized.
    """

    loader = StrawberrySQLAlchemyLoader(async_bind_factory=get_session_factory())

    class CustomInfo(Info):
        @property
        def context(self) -> ContextType:  # type: ignore[type-var]
            return typing.cast(ContextType, {"sqlalchemy_loader": loader, "compiler_service": context.compiler_service})

    @strawberry.type
    class Query:
        @strawberry.field
        async def environments(
            self,
            info: CustomInfo,
            first: typing.Optional[int] = strawberry.UNSET,
            after: typing.Optional[str] = strawberry.UNSET,
            last: typing.Optional[int] = strawberry.UNSET,
            before: typing.Optional[str] = strawberry.UNSET,
            filter: typing.Optional[EnvironmentFilter] = strawberry.UNSET,
            order_by: typing.Optional[Sequence[EnvironmentOrder]] = strawberry.UNSET,
        ) -> relay.ListConnection[Environment]:
            stmt = select(models.Environment)
            stmt = add_filter_and_sort(stmt, EnvironmentOrder.default_order(), filter, order_by)
            return await get_connection(
                stmt, info=info, model="Environment", first=first, after=after, last=last, before=before
            )

        @strawberry.field
        async def notifications(
            self,
            info: CustomInfo,
            filter: NotificationFilter,
            first: typing.Optional[int] = strawberry.UNSET,
            after: typing.Optional[str] = strawberry.UNSET,
            last: typing.Optional[int] = strawberry.UNSET,
            before: typing.Optional[str] = strawberry.UNSET,
            order_by: typing.Optional[Sequence[NotificationOrder]] = strawberry.UNSET,
        ) -> relay.ListConnection[Notification]:
            stmt = select(models.Notification)
            stmt = add_filter_and_sort(stmt, NotificationOrder.default_order(), filter, order_by)
            return await get_connection(
                stmt, info=info, model="Notification", first=first, after=after, last=last, before=before
            )

        @strawberry.field
        async def resources(
            self,
            info: CustomInfo,
            filter: ResourceFilter,
            first: typing.Optional[int] = strawberry.UNSET,
            after: typing.Optional[str] = strawberry.UNSET,
            last: typing.Optional[int] = strawberry.UNSET,
            before: typing.Optional[str] = strawberry.UNSET,
            order_by: typing.Optional[Sequence[ResourceOrder]] = strawberry.UNSET,
        ) -> relay.ListConnection[Resource]:
            if filter.is_orphan is False:
                include_orphans = False
            else:
                include_orphans = True

            # Only fetch resources in their latest version
            # Logic based on src/inmanta/data/dataview.py::ResourceView
            stmt = select(models.Resource).where(models.Resource.environment == filter.environment)
            # CTE that fetches the latest scheduled version
            latest_scheduled_version_cte = (
                select(models.Scheduler.last_processed_model_version.label("version"))
                .where(models.Scheduler.environment == filter.environment)
                .cte()
            )

            if include_orphans:
                # CTE that checks if a resource is orphaned or not and returns the appropriate version
                # - If it is not orphaned, return the resource in the latest released version
                # - If it is orphaned, return the resource in the latest version that it was present in.
                included_orphans_cte = (
                    select(
                        models.ResourcePersistentState.environment,
                        models.ResourcePersistentState.resource_id,
                        case(
                            # Simple case where we are dealing with non-orphans
                            (
                                not_(models.ResourcePersistentState.is_orphan),
                                select(latest_scheduled_version_cte.c.version).scalar_subquery(),
                            ),
                            else_=select(func.max(models.t_resource_set_configuration_model.c.model))
                            .join(
                                models.Resource,
                                and_(
                                    models.Resource.environment == models.t_resource_set_configuration_model.c.environment,
                                    models.Resource.resource_set == models.t_resource_set_configuration_model.c.resource_set,
                                ),
                            )
                            .join(
                                models.Configurationmodel,
                                and_(
                                    models.t_resource_set_configuration_model.c.environment
                                    == models.Configurationmodel.environment,
                                    models.t_resource_set_configuration_model.c.model == models.Configurationmodel.version,
                                ),
                            )
                            .where(
                                models.Resource.environment == models.ResourcePersistentState.environment,
                                models.Resource.resource_id == models.ResourcePersistentState.resource_id,
                                models.Configurationmodel.released.is_(True),
                            )
                            .scalar_subquery(),
                        ).label("version"),
                    )
                    .where(
                        models.ResourcePersistentState.environment == filter.environment,
                    )
                    .cte()
                )
                stmt = stmt.join(
                    models.t_resource_set_configuration_model,
                    and_(
                        models.t_resource_set_configuration_model.c.environment == models.Resource.environment,
                        models.t_resource_set_configuration_model.c.resource_set == models.Resource.resource_set,
                    ),
                ).join(
                    included_orphans_cte,
                    and_(
                        models.Resource.environment == included_orphans_cte.c.environment,
                        models.Resource.resource_id == included_orphans_cte.c.resource_id,
                        models.t_resource_set_configuration_model.c.model == included_orphans_cte.c.version,
                    ),
                )
            else:
                stmt = stmt.join(
                    models.t_resource_set_configuration_model,
                    and_(
                        models.t_resource_set_configuration_model.c.environment == models.Resource.environment,
                        models.t_resource_set_configuration_model.c.resource_set == models.Resource.resource_set,
                        models.t_resource_set_configuration_model.c.model
                        == select(latest_scheduled_version_cte.c.version).scalar_subquery(),
                    ),
                )
            stmt = add_filter_and_sort(stmt, ResourceOrder.default_order(), filter, order_by)
            stmt = do_required_resource_joins(stmt, filter, order_by)
            return await get_connection(stmt, info=info, model="Resource", first=first, after=after, last=last, before=before)

    return strawberry.Schema(query=Query, config=StrawberryConfig(info_class=CustomInfo))
