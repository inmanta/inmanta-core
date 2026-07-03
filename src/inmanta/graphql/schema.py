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
import inspect
import re
import typing
import uuid
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Mapping, Sequence, cast

import docstring_parser

import inmanta.data.sqlalchemy as models
import strawberry
from inmanta import data
from inmanta.data import get_session, get_session_factory, model
from inmanta.deploy import state
from inmanta.server.services.compilerservice import CompilerService
from sqlakeyset import Marker, unserialize_bookmark
from sqlakeyset.asyncio import select_page
from sqlalchemy import Boolean, Select, UnaryExpression, and_, asc, desc, func, not_, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapper
from strawberry import relay, scalars
from strawberry.relay import Node, NodeType
from strawberry.scalars import JSON
from strawberry.schema.config import StrawberryConfig
from strawberry.types import Info
from strawberry.types.field import field
from strawberry.types.info import ContextType
from strawberry.types.nodes import SelectedField, Selection
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyLoader, StrawberrySQLAlchemyMapper
from strawberry_sqlalchemy_mapper.mapper import (
    _GENERATED_FIELD_KEYS_KEY,
    _IS_GENERATED_CONNECTION_TYPE_KEY,
    BaseModelType,
    SkipTypeSentinel,
    StrawberrySQLAlchemyLazy,
)

"""
The strawberry models in this file are mapped from the sqlalchemy models in inmanta.data.sqlalchemy.models.
We use a `StrawberrySQLAlchemyMapper` to map a sqlalchemy model to a strawberry model via the `type` decorator.

There are 4 important building blocks that we have to take into account:
    1) The strawberry output type. Instead of decorating a class directly, we declare the core fields on a plain
        "core mixin" i.e.
        ```
            class CoreEnvironmentMixin:
                __exclude__ = [
                    "project_",
                    "schedulersession",
                    ...
                ]
                is_expert_mode: bool = strawberry.field(resolver=get_expert_mode)
                is_compiling: bool = strawberry.field(resolver=get_is_compiling)
        ```
         `get_schema` then builds the actual strawberry type from this mixin (plus any extension contributions, see
         `GraphQLContribution`) and maps it onto the SQLAlchemy model with `@mapper.type(<respective_sqlalchemy_model>)`
         via `build_strawberry_output_type`.
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
            ) -> CustomListConnection[Environment]:
                stmt = select(models.Environment)
                stmt = add_filter_and_sort(
                    stmt, EnvironmentOrder.default_order(), [filter] if is_provided(filter) else [], order_by
                )
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

                def apply_filter[*Ts](self, stmt: Select[tuple[*Ts]], model: type[models.Base], key: str) -> Select[tuple[*Ts]]:
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
        - No support for sqlalchemy's column_property:
            https://github.com/strawberry-graphql/strawberry-sqlalchemy/issues/125

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


@strawberry.type(name="Connection", description="My connection to a list of items.")
# use NodeType imported type var because strawberry does some fishy type var introspection
class CustomListConnection(relay.ListConnection[NodeType]):
    """
    Custom implementation of relay.ListConnection.

    This class defines what will appear on the GraphQL introspection schema.
    It is also used by strawberry for validation against an incoming GraphQL query.
    """

    total_count: int | None = field(description="Total number of results for this connection")


def _build_docstring_param_cache() -> dict[str, dict[str, str]]:
    """
    Build a mapping from table name to a dict of param name -> description, parsed from
    :param docstrings on BaseDocument subclasses. Called once at import time.
    """
    import inspect

    cache: dict[str, dict[str, str]] = {}
    for _name, cls in inspect.getmembers(data, inspect.isclass):
        if not issubclass(cls, data.BaseDocument) or cls is data.BaseDocument:
            continue
        doc = cls.__doc__
        if not doc:
            continue
        try:
            parsed = docstring_parser.parse(doc, style=docstring_parser.DocstringStyle.REST)
        except docstring_parser.ParseError:
            continue
        param_map = {p.arg_name: p.description for p in parsed.params if p.description}
        if param_map:
            cache[cls.table_name()] = param_map
    return cache


_docstring_param_cache: dict[str, dict[str, str]] = _build_docstring_param_cache()


class CustomStrawberrySQLAlchemyMapper(StrawberrySQLAlchemyMapper[BaseModelType]):
    """
    Custom StrawberrySQLAlchemyMapper used to overwrite specific methods.
    Useful when we want to change how Connections/Edges are created.

    The classes generated by this (and the default) mapper are generated in runtime.
    """

    def _handle_columns(
        self,
        mapper: Mapper[typing.Any],
        type_: typing.Any,
        excluded_keys: typing.Iterable[str],
        generated_field_keys: typing.List[str],
    ) -> None:
        """
        Populate the Strawberry type with fields derived from the SQLAlchemy mapper.
        Override to propagate SQLAlchemy column and relationship ``doc`` to GraphQL field descriptions.

        Despite the original method only working for sqlalchemy columns, this override also generates fields for relationships
        and hybrid properties.

        Field descriptions are resolved in order of precedence:
        1. SQLAlchemy ``doc`` attribute
        2. ``:param`` docstring on the corresponding ``BaseDocument`` subclass

        :param mapper: The sqlalchemy mapper that describes the ORM model.
        :param type_: The Strawberry GraphQL type currently being constructed.
        :param excluded_keys: A list of keys we want to exclude from the strawberry model (taken from the __exclude__ attr).
        :param generated_field_keys: A list that is populated with the names of fields generated by this method.
        """

        table_name: str = mapper.entity.__tablename__
        docstring_params = _docstring_param_cache.get(table_name, {})

        def _should_skip(attr_key: str) -> bool:
            """
            Checks if we should skip generating this attribute.
            """
            return attr_key in excluded_keys or attr_key in type_.__annotations__ or hasattr(type_, attr_key)

        def _add_field(
            attr_key: str,
            annotation: typing.Any,
            description: str | None = None,
            connection_resolver: typing.Callable[..., typing.Awaitable[typing.Any]] | None = None,
        ) -> None:
            """
            Creates the StrawberrySQLAlchemy field with the given description.
            """
            type_.__annotations__[attr_key] = annotation
            f = (
                field(description=description, resolver=connection_resolver)
                if connection_resolver
                else field(description=description)
            )
            setattr(type_, attr_key, f)
            generated_field_keys.append(attr_key)

        # Columns
        for key, column in mapper.columns.items():
            if _should_skip(key):
                continue

            item_type = self._convert_column_to_strawberry_type(column)
            if item_type is SkipTypeSentinel:
                continue

            doc = column.doc or docstring_params.get(key)
            _add_field(key, item_type, description=doc)

        # Relationships
        for key, relationship in mapper.relationships.items():
            if _should_skip(key):
                continue

            relationship_type = self._convert_relationship_to_strawberry_type(
                relationship,
                True,
            )

            doc = relationship.doc or docstring_params.get(key)

            resolver = self.connection_resolver_for(
                relationship,
                True,
            )

            _add_field(key, relationship_type, description=doc, connection_resolver=resolver)

        # Hybrid Properties
        # Currently only used for Resource.compliance
        for key, descriptor in mapper.all_orm_descriptors.items():
            if not isinstance(descriptor, hybrid_property) or _should_skip(key):
                continue

            func = descriptor.fget

            return_type = typing.get_type_hints(func).get("return")
            if return_type is None:
                continue

            doc = inspect.getdoc(func) or docstring_params.get(key)

            _add_field(key, return_type, description=doc)

    def _connection_type_for(self, type_name: str) -> typing.Type[typing.Any]:
        """
        We overwrite this method in order to inject `total_count` into the generated ListConnections.

        It is important to keep this method in sync with our implementation of CustomListConnection so that we don't have
        inconsistencies between the class generated at runtime and the class used for typing/validation.
        """
        connection_name = f"{type_name}Connection"
        if connection_name not in self.connection_types:
            edge_type = self._edge_type_for(type_name)
            lazy_type = StrawberrySQLAlchemyLazy(type_name=type_name, mapper=self)
            self.connection_types[connection_name] = connection_type = strawberry.type(
                dataclasses.make_dataclass(
                    connection_name,
                    [
                        ("edges", typing.List[edge_type]),  # type: ignore[valid-type]
                        ("total_count", typing.Optional[int], field(default=None)),
                    ],
                    bases=(CustomListConnection[lazy_type],),  # type: ignore[valid-type]
                )
            )
            setattr(connection_type, _GENERATED_FIELD_KEYS_KEY, ["edges", "total_count"])
            setattr(connection_type, _IS_GENERATED_CONNECTION_TYPE_KEY, True)
        return self.connection_types[connection_name]


# We set always_use_list to true because we don't support pagination for nested entities
mapper: CustomStrawberrySQLAlchemyMapper[typing.Any] = CustomStrawberrySQLAlchemyMapper(always_use_list=True)
DEFAULT_PER_PAGE: int = 50


def is_provided[T](value: T | None) -> typing.TypeGuard[T]:
    """
    Checks if a filter field was provided by the user, i.e. it is neither None nor strawberry.UNSET.

    This is a TypeGuard so that mypy narrows away the `None` (and `strawberry.UNSET`) in the positive branch,
    just like an inline `value is not None and value is not strawberry.UNSET` check would.
    """
    return value is not None and value is not strawberry.UNSET


def walk_selected_fields(selection: Selection) -> typing.Iterator[SelectedField]:
    """
    Yield every SelectedField in a selection subtree: the selection itself if it is a field, plus all nested
    selections, recursing through inline (`... on Type`) and named (`...Fragment`) fragments.

    :param selection: the root of the selection subtree to walk.
    """
    if isinstance(selection, SelectedField):
        yield selection
    for sub_selection in selection.selections or []:
        yield from walk_selected_fields(sub_selection)


def get_selected_field_names(info: Info) -> set[str]:
    """
    Return the (camelCase) names of every field selected anywhere in the query, recursing through nested
    selections and fragments. This includes the names of the top-level resolved fields themselves (e.g. `resources`);

    :param info: the Strawberry resolver info holding the selected fields of the current query.
    """
    return {field.name for selected_field in info.selected_fields for field in walk_selected_fields(selected_field)}


def is_field_selected(info: Info, field_name: str) -> bool:
    """
    Check whether the user requested `field_name` anywhere in the query, including nested fields and fragments.

    :param info: the Strawberry resolver info holding the selected fields of the current query.
    :param field_name: the (camelCase) name of the field to look for.
    """
    return field_name in get_selected_field_names(info)


def to_snake_case(name: str) -> str:
    """
    Convert a string from camelCase to snake_case.
    Strawberry converts the query, filter and order fields to camelCase.
    With this we accommodate the user to also filter and order in camelCase.
    """
    if re.match(r"[A-Z]", name):
        raise Exception("name cannot start with capital letter.")
    return re.sub("([A-Z])", r"_\1", name).lower()


# The name of a GraphQL output type (e.g. "Resource"). Also the key extension contributions for that type are grouped
# under, both in `GraphQLSlice` and in the mapping passed to `get_schema`.
type GraphQLTypeName = str


def graphql_type_name(model: type[models.Base]) -> GraphQLTypeName:
    """
    The name of the GraphQL output type that is built for a SQLAlchemy model. By convention it is the model's class
    name (e.g. `models.Resource` -> "Resource"). This is the single place that convention lives.

    :param model: the SQLAlchemy model whose GraphQL output type name is returned.
    """
    return model.__name__


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
    def apply_filter[*Ts](self, stmt: Select[tuple[*Ts]], model: type[models.Base], key: str) -> Select[tuple[*Ts]]:
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

    def apply_filter[*Ts](self, stmt: Select[tuple[*Ts]], model: type[models.Base], key: str) -> Select[tuple[*Ts]]:
        # Enums are stored as a string of their name in the database and not of their value
        if is_provided(self.eq):
            stmt = stmt.where(getattr(model, key).in_([x.name for x in self.eq]))
        if is_provided(self.neq):
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

    def apply_filter[*Ts](self, stmt: Select[tuple[*Ts]], model: type[models.Base], key: str) -> Select[tuple[*Ts]]:
        if is_provided(self.eq):
            stmt = stmt.where(getattr(model, key).in_(self.eq))
        if is_provided(self.neq):
            stmt = stmt.where(not_(getattr(model, key).in_(self.neq)))
        if is_provided(self.contains):
            for c in self.contains:
                stmt = stmt.where(getattr(model, key).ilike(c))
        if is_provided(self.not_contains):
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
        filter_dict = {}
        for key, value in self.__dict__.items():
            if value is strawberry.UNSET:
                raise ValueError(f"Filter {key} was requested but no value was provided")
            filter_dict[key] = value
        return filter_dict

    def apply_filter[*Ts](self, stmt: Select[tuple[*Ts]]) -> Select[tuple[*Ts]]:
        """
        Applies the filters to the given query.
        """
        return stmt.filter_by(**self.get_filter_dict())


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


def get_expert_mode(root: "CoreEnvironmentMixin") -> bool:
    """
    Checks settings of environment to figure out if expert mode is enabled or not
    """
    assert hasattr(root, "settings")  # Make mypy happy
    assert isinstance(root.settings, dict)
    if "enable_lsm_expert_mode" not in root.settings["settings"]:
        return False
    return cast(bool, root.settings["settings"]["enable_lsm_expert_mode"]["value"])


def get_is_compiling(root: "CoreEnvironmentMixin", info: strawberry.Info) -> bool:
    """
    Checks compiler service to figure out if environment is compiling or not
    """
    compiler_service = info.context.get("compiler_service", None)
    assert isinstance(compiler_service, CompilerService)
    assert hasattr(root, "id")  # Make mypy happy
    return compiler_service.is_environment_compiling(environment_id=root.id)


def get_settings(root: "CoreEnvironmentMixin") -> scalars.JSON:
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


class CoreEnvironmentMixin:
    """
    Mixin carrying the core Environment output fields. It is merged with the extensions' output mixins (and mapped onto
    the SQLAlchemy Environment model) by `build_strawberry_output_type` to build the `Environment` GraphQL output type.
    """

    # Add every relation/attribute that we don't want to expose in our GraphQL endpoint to `__exclude__`
    __exclude__ = [
        "project_",
        "schedulersession",
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
    is_expert_mode: bool = strawberry.field(
        resolver=get_expert_mode, description="Is the expert mode enabled on this environment?"
    )
    is_compiling: bool = strawberry.field(
        resolver=get_is_compiling, description="Is there a compile running on this environment?"
    )
    settings: scalars.JSON = strawberry.field(resolver=get_settings, description="The settings for this environment.")


@strawberry.input
class EnvironmentFilter(StrawberryFilter):
    id: typing.Optional[uuid.UUID] = strawberry.UNSET


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


class CoreNotificationMixin:
    """
    Mixin carrying the core Notification output fields. It is merged with the extensions' output mixins (and mapped onto
    the SQLAlchemy Notification model) by `build_strawberry_output_type` to build the `Notification` GraphQL output type.
    """

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


def get_requires_length(root: "CoreResourceMixin") -> int:
    """
    Checks the length of the requires of the resource
    """
    assert hasattr(root, "attributes")  # Make mypy happy
    return len(root.attributes.get("requires", []))


def get_purged(root: "CoreResourceMixin") -> bool:
    """
    Checks the state of the purged attribute on this resource
    """
    assert hasattr(root, "attributes")  # Make mypy happy
    return bool(root.attributes.get("purged"))


class CoreResourceMixin:
    """
    Mixin carrying the core Resource output fields. It is merged with the extensions' output mixins (and mapped onto
    the SQLAlchemy Resource model) by `build_strawberry_output_type` to build the `Resource` GraphQL output type.
    """

    __exclude__ = ["resource_set_"]
    requires_length: int = strawberry.field(
        resolver=get_requires_length, description="The length of the requires of this resource."
    )
    purged: bool = strawberry.field(
        resolver=get_purged, description="Checks the state of the purged attribute on this resource"
    )


@dataclasses.dataclass(kw_only=True)
@strawberry.input
class ResourceFilterABC(StrawberryFilter):
    """
    Abstract base class that defines the shared attributes/behaviour of every resource filter component: core's
    `CoreResourceFilter` and each extension's filter (contributed via `GraphQLContribution.get_resource_filter_input_class`).
    These components are composed into the single `ResourceFilter` GraphQL input type exposed on the `resources` query
    (see `get_resource_filter_components` and `get_schema`).

    :param environment: The environment the resources belong to.
    """

    environment: uuid.UUID

    def handles_version(self) -> bool:
        """
        Return True if this filter component takes over selection of the model version from core. At most one
        component may do so; when none does, core (`CoreResourceFilter`) selects the version by default.
        """
        return False

    def apply_version_filter[*Ts](self, stmt: Select[tuple[*Ts]]) -> Select[tuple[*Ts]]:
        """
        Restrict the query to the appropriate version(s) of the model. Only invoked on the single component
        responsible for version selection: an extension whose `handles_version()` is True, or core otherwise.
        """
        raise NotImplementedError()


@dataclasses.dataclass(kw_only=True)
@strawberry.input
class CoreResourceFilter(ResourceFilterABC):
    resource_type: StrFilter | None = strawberry.UNSET
    resource_id_value: StrFilter | None = strawberry.UNSET
    agent: StrFilter | None = strawberry.UNSET
    purged: bool | None = strawberry.UNSET
    blocked: EnumFilter[state.Blocked] | None = strawberry.UNSET
    compliance: EnumFilter[state.Compliance] | None = strawberry.UNSET
    last_handler_run: EnumFilter[state.HandlerResult] | None = strawberry.UNSET
    is_deploying: bool | None = strawberry.UNSET
    is_orphan: bool | None = strawberry.UNSET
    model_version: int | None = strawberry.UNSET

    @property
    def model(self) -> type[models.Base]:
        return models.Resource

    @property
    def rps_model(self) -> type[models.Base]:
        return models.ResourcePersistentState

    def handles_version(self) -> bool:
        # is_orphan and model_version both control which version(s) of the model are selected, so providing either
        # means core owns version selection. This also lets us detect a conflict when an extension tries to take it over.
        return is_provided(self.is_orphan) or is_provided(self.model_version)

    def apply_version_filter[*Ts](self, stmt: Select[tuple[*Ts]]) -> Select[tuple[*Ts]]:
        # Determine which version of the model each resource should be taken from:
        #  - if a specific version was requested, pin every resource set to that version
        #  - otherwise take each resource at the latest scheduled version, except orphaned resources which are
        #    taken at the last version they were present in (orphaned_after). ResourcePersistentState is already
        #    joined onto the query, so orphaned_after is available directly (no extra CTE/join needed). For
        #    non-orphaned resources orphaned_after is NULL, so coalesce falls back to the latest scheduled version.
        version = (
            self.model_version
            if is_provided(self.model_version)
            else func.coalesce(
                models.ResourcePersistentState.orphaned_after,
                select(models.Scheduler.last_processed_model_version)
                .where(models.Scheduler.environment == self.environment)
                .scalar_subquery(),
            )
        )
        return stmt.join(
            models.t_resource_set_configuration_model,
            and_(
                models.t_resource_set_configuration_model.c.environment == models.Resource.environment,
                models.t_resource_set_configuration_model.c.resource_set == models.Resource.resource_set,
                models.t_resource_set_configuration_model.c.model == version,
            ),
        )

    def apply_filter[*Ts](
        self, stmt: Select[tuple[*Ts]]
    ) -> Select[tuple[*Ts]]:  # Every filter we apply to the resource is custom, so we don't use `get_filter_dict`
        rps_keys = [
            "resource_type",
            "resource_id_value",
            "agent",
            "blocked",
            "compliance",
            "last_handler_run",
        ]
        for key in rps_keys:
            attr: CustomFilter | None = getattr(self, key)
            if is_provided(attr):
                stmt = attr.apply_filter(stmt, self.rps_model, key)
        if is_provided(self.environment):
            stmt = stmt.filter(models.ResourcePersistentState.environment == self.environment)
        if is_provided(self.purged):
            stmt = stmt.filter(models.Resource.attributes["purged"].astext.cast(Boolean).is_(self.purged))
        if is_provided(self.is_deploying):
            stmt = stmt.filter(models.ResourcePersistentState.is_deploying == self.is_deploying)
        if is_provided(self.is_orphan):
            stmt = stmt.filter(models.ResourcePersistentState.is_orphan.is_(self.is_orphan))
        return stmt


class ResourceOrder(StrawberryOrder):

    @classmethod
    def default_order(cls) -> dict[str, UnaryExpression[typing.Any]]:
        return {
            "resource_id": asc(models.ResourcePersistentState.resource_id),
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
            "agent": self.rps_model,
            "resource_type": self.rps_model,
            "resource_id_value": self.rps_model,
            "blocked": self.rps_model,
            "compliance": self.rps_model,
            "last_handler_run": self.rps_model,
            "is_deploying": self.rps_model,
        }


@mapper.type(models.ResourcePersistentState)
class ResourcePersistentState:
    __tablename__ = "resource_persistent_state"
    __exclude__ = ["resource_set_", "environment_"]


@strawberry.type
class ComposedResourceSummary:
    """
    Modeled after inmanta.data.model.ComposedResourceSummary.

    Summary of the composed status of all resources in an environment.
    """

    total_count: int = strawberry.field(description="The total number of resources in the environment.")
    last_handler_run: JSON = strawberry.field(
        description="Summary of the last handler run for all resources in the environment."
    )
    blocked: JSON = strawberry.field(description="Summary of the blocked status of all resources in the environment.")
    compliance: JSON = strawberry.field(description="Summary of the compliance status of all resources in the environment.")
    is_deploying: JSON = strawberry.field(description="Summary of the execution status of all resources in the environment.")


def add_filter_and_sort[*Ts](
    stmt: Select[tuple[*Ts]],
    default_sorting: dict[str, UnaryExpression[typing.Any]],
    filter: Sequence[StrawberryFilter] = (),
    order_by: typing.Optional[Sequence[StrawberryOrder]] = strawberry.UNSET,
) -> Select[tuple[*Ts]]:
    """
    Adds filter and sorting to the given statement.

    :param filter: the filter components to apply. A single query can have several components: the `resources` query
        composes core and extension filters, while the other queries pass a single (or no) filter.
    """
    for filter_component in filter:
        stmt = filter_component.apply_filter(stmt)
    order_expressions: dict[str, UnaryExpression[typing.Any]] = {}
    if is_provided(order_by):
        for order in order_by:
            if order.key in order_expressions:
                raise Exception(f"Sorting key appears multiple times in orderBy: {order.key}")
            order_expressions[order.key] = order.get_order_by()
    for default_key, order_expression in default_sorting.items():
        if default_key not in order_expressions:
            order_expressions[default_key] = order_expression
    stmt = stmt.order_by(*order_expressions.values())
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


async def get_connection[*Ts](
    stmt: Select[tuple[*Ts]],
    model: str,
    info: Info,
    first: typing.Optional[int] = strawberry.UNSET,
    after: typing.Optional[str] = strawberry.UNSET,
    last: typing.Optional[int] = strawberry.UNSET,
    before: typing.Optional[str] = strawberry.UNSET,
    count_stmt: Select[tuple[int]] | None = None,
) -> CustomListConnection[Node]:
    """
    Build the connection object. Here we do all the pagination and fetching of results (edges) to return to the user.
    We do not call `ListConnection.resolve_connection` because:
     1) We already got the PageInfo arguments from sqlakeyset
     2) It calls `Edge.resolve_edge` with a cursor that is not useful to us
    """
    async with get_session() as session:
        per_page: int
        # Get results per page and sanitation of input arguments
        if is_provided(first):
            if is_provided(last) or is_provided(before):
                raise Exception("`first` is not allowed in conjunction with `last` or `before`")
            per_page = first
        elif is_provided(last):
            if is_provided(after) or not is_provided(before):
                raise Exception("`last` is only allowed in conjunction with `before`")
            per_page = last
        else:
            per_page = DEFAULT_PER_PAGE

        # Check if we requested total_count
        total_count: int | None = None
        if is_field_selected(info, "totalCount"):
            if count_stmt is None:
                count_stmt = select(func.count()).select_from(stmt.subquery())
            count_result = await session.execute(count_stmt)
            total_count = count_result.scalar_one()

        # Get cursor and direction of results to fetch (forwards/backwards)
        page: Marker | None = None
        if is_provided(after):
            if is_provided(before):
                raise Exception("`after` is not allowed in conjunction with `before`")
            page = unserialize_bookmark(f">{decode_cursor(after)}")
        elif is_provided(before):
            page = unserialize_bookmark(f"<{decode_cursor(before)}")

        # Fetch the page using sqlakeyset
        result = await select_page(session, stmt, per_page=per_page, page=page)
        edges = []
        # We use the private methods for the mapper because their respective public attributes like `mapper.connection_types`
        # Are only filled when the private methods are called first. The private methods use the public attributes as cache so
        # it is fine to call them repeatedly
        connection = cast(type[CustomListConnection[Node]], mapper._connection_type_for(model))

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
            total_count=total_count,
        )


class GraphQLContribution(ABC):
    """
    Extension hook that lets extensions (e.g. LSM) contribute extra information to a single GraphQL output type
    without a tight coupling between core and these extensions.

    A contribution targets one object type (the one returned by `get_target_model`, e.g. `models.Resource`).
    An extension that wants to extend several object types registers one contribution per type.
    Core groups the contributions by target type and, for each type, merges them onto the
    GraphQL output type and its backing SQLAlchemy model (see `build_strawberry_output_type` and
    `build_composed_sqlalchemy_model`).
    """

    @classmethod
    @abstractmethod
    def get_target_model(cls) -> type[models.Base]:
        """
        Return the SQLAlchemy model of the object type this contribution extends (e.g. `models.Resource`). It
        determines which GraphQL output type the contribution is merged into.
        """
        ...

    @classmethod
    def get_graphql_output_type_mixin(cls) -> type | None:
        """
        Return a plain class (no decorator) whose `strawberry.field` declarations are merged into the target
        output type. These output fields can be sqlalchemy columns that are later populated with `populate_sqlalchemy_columns`
        or simple resolvers (e.g. `purged` on `CoreResourceMixin`).
        Return None if this contribution adds no output fields.
        """
        return None

    @classmethod
    def get_sqlalchemy_columns(cls) -> "typing.Mapping[str, object]":
        """
        Return SQLAlchemy column descriptors (e.g. `query_expression()`) keyed by attribute name. These are
        merged onto a dynamically built subclass of the target model, so the query can select a single ORM object
        that carries extra, SQL-backed columns (joins/subqueries) that don't live on the target's table. The value
        of each column is populated per query by `populate_sqlalchemy_columns`.

        For each column declared here, the matching output field should also be declared with a concrete type on
        the mixin returned by `get_graphql_output_type_mixin` (otherwise the mapper would try to
        auto-map the untyped column).
        """
        return {}

    @classmethod
    def populate_sqlalchemy_columns[*Ts](
        cls, stmt: "Select[tuple[*Ts]]", model: type[models.Base], requested_fields: typing.AbstractSet[str]
    ) -> "Select[tuple[*Ts]]":
        """
        Populate the columns declared in `get_sqlalchemy_columns` onto the query, typically via sqlalchemy's
        `with_expression`.
        Populating a column is usually expensive (extra joins/subqueries), so an implementation should only
        populate the columns whose name is in `requested_fields` and leave the rest as their (null)
        `query_expression` default. Name columns distinctly to avoid colliding with unrelated fields in the set.

        :param stmt: the query the columns are populated onto. Implementations should return it with their columns
            added (e.g. via `with_expression`).
        :param model: the dynamically built subclass of the target model that carries the `query_expression()`
            placeholders (so its core columns keep their type, while the extra columns are read with `getattr`).
        :param requested_fields: the (snake_case) names of every field selected anywhere in the GraphQL query
            (not only the target's output fields), so a column counts as requested when its name appears in the set.
        """
        return stmt

    @classmethod
    def get_resource_filter_input_class(cls) -> "type[ResourceFilterABC] | None":
        """
        Return a `ResourceFilterABC` subclass (a `@strawberry.input`) whose fields are composed into the `resources`
        query's `ResourceFilter` input type, letting this extension filter resources on its own fields. The class'
        `apply_filter` is applied alongside core's, and it may take over version selection via `handles_version` /
        `apply_version_filter`. Only meaningful for a contribution targeting `models.Resource`; return None (the
        default) to contribute no filter fields.
        """
        return None


def build_composed_sqlalchemy_model(
    base_model: type[models.Base],
    contributions: Sequence[type[GraphQLContribution]],
) -> type[models.Base]:
    """
    Build the SQLAlchemy model backing an output type.

    Extensions can contribute SQLAlchemy columns (`get_sqlalchemy_columns`). When any are contributed we build a
    subclass of `base_model` that carries them (single-table inheritance: same table, extra mapped columns), so each
    row the query selects is a single ORM object that can carry the extra columns; otherwise `base_model` is used
    directly. get_schema is called once per process, so a fixed class name is fine.

    The returned model is needed by the query to select the right entity and let extensions populate their columns,
    and by `build_strawberry_output_type` to map the Strawberry output type from it.

    :param base_model: the SQLAlchemy model of the object type being built (e.g. `models.Resource`)
    :param contributions: the extension contributions that target `base_model`
    """
    sqlalchemy_columns: dict[str, object] = {}
    for c in contributions:
        for name, column in c.get_sqlalchemy_columns().items():
            if name in sqlalchemy_columns:
                raise Exception(f"Column {name} defined more than once in {graphql_type_name(base_model)} contributions.")
            sqlalchemy_columns[name] = column
    if not sqlalchemy_columns:
        return base_model
    return cast(
        type[models.Base],
        type(f"Composed{base_model.__name__}", (base_model,), sqlalchemy_columns),
    )


def build_strawberry_output_type(
    type_name: str,
    model: type[models.Base],
    core_mixin: type,
    contributions: Sequence[type[GraphQLContribution]],
) -> type:
    """
    Build a GraphQL output type used by Strawberry, mapped from `model`.

    The core fields (carried by `core_mixin`) are merged with the output mixins contributed by extensions
    (`get_graphql_output_type_mixin`) whose `strawberry.field` declarations are added to the output type.

    :param type_name: the name of the GraphQL output type to build (e.g. "Resource")
    :param model: the SQLAlchemy model that backs the output type (see `build_composed_sqlalchemy_model`)
    :param core_mixin: the mixin carrying the core output fields for this type (e.g. `CoreResourceMixin`)
    :param contributions: the extension contributions that target this type
    """
    mixins: tuple[type, ...] = tuple(mixin for c in contributions if (mixin := c.get_graphql_output_type_mixin()) is not None)
    annotations: dict[str, object] = {}
    attrs: dict[str, object] = {}
    excludes: list[str] = []
    for base in (core_mixin, *mixins):
        annotations.update(base.__dict__.get("__annotations__", {}))
        excludes += base.__dict__.get("__exclude__", [])
        for k, v in base.__dict__.items():
            if not k.startswith("__"):  # Exclude private attributes. Annotations and exclude are dealt separately
                if k not in attrs:
                    attrs[k] = v
                else:
                    raise Exception(f"{k} defined more than once in {type_name} mixins.")

    # Can't do the same as the filter input type because the mixins can't have the mapper.type decorator and that is required
    return cast(
        type,
        mapper.type(model)(type(type_name, (), {"__annotations__": annotations, "__exclude__": excludes, **attrs})),
    )


def get_resource_filter_components(
    contributions: Sequence[type[GraphQLContribution]],
) -> tuple[type[ResourceFilterABC], ...]:
    """
    Return the filter components that compose the `resources` query's `ResourceFilter` input type: `CoreResourceFilter`
    followed by every extension-contributed filter class (see `GraphQLContribution.get_resource_filter_input_class`).
    `get_schema` builds the composed input type from these by multiple inheritance, and the `resources` resolver
    decomposes the received filter back into one instance per component to apply them.

    :param contributions: the extension contributions that target `models.Resource`.
    """
    extension_filters: list[type[ResourceFilterABC]] = [
        cls for c in contributions if (cls := c.get_resource_filter_input_class()) is not None
    ]
    return (CoreResourceFilter, *extension_filters)


# The object types extensions can register GraphQL contributions for (see GraphQLContribution), mapping each SQLAlchemy
# model to the mixin carrying its core output fields. `get_schema` composes each of these from the core mixin and the
# registered contributions; registrations for any other model are rejected. The GraphQL output type name is always the
# model's class name (e.g. `models.Resource` -> "Resource"), which is also the key the contributions are grouped under.
REGISTRABLE_MODELS: "Mapping[type[models.Base], type]" = {
    models.Resource: CoreResourceMixin,
    models.Environment: CoreEnvironmentMixin,
    models.Notification: CoreNotificationMixin,
}


def get_schema(
    context: GraphQLContext,
    extension_contributions: "Mapping[GraphQLTypeName, Sequence[type[GraphQLContribution]]]",
) -> strawberry.Schema:
    """
    Initializes the Strawberry GraphQL schema.
    It is initiated in a function instead of being declared at the module level, because we have to do this
    after the SQLAlchemy engine is initialized.

    :param context: the GraphQL context made available to resolvers (e.g. to reach the compiler service).
    :param extension_contributions: the registered extension contributions, grouped by the name of the GraphQL output
        type they target (see `graphql_type_name`). Extension names are not relevant here, so they are dropped by the
        caller (`GraphQLSlice`).
    """

    loader = StrawberrySQLAlchemyLoader(async_bind_factory=get_session_factory())

    def build_output_type(base_model: type[models.Base], core_mixin: type) -> tuple[type[models.Base], type]:
        """
        Build the (possibly extension-composed) SQLAlchemy model and Strawberry output type for one object type.
        Returns the SQLAlchemy model to select in the query (a subclass carrying the extensions' extra columns when
        there are any, `base_model` otherwise) and the Strawberry output type to return.

        :param base_model: the SQLAlchemy model of the object type being built (e.g. `models.Resource`).
        :param core_mixin: the mixin carrying the core output fields for this type (e.g. `CoreResourceMixin`).
        """
        type_name = graphql_type_name(base_model)
        contributions = extension_contributions.get(type_name, [])
        composed_model = build_composed_sqlalchemy_model(base_model, contributions)
        output_type = build_strawberry_output_type(type_name, composed_model, core_mixin, contributions)
        return composed_model, output_type

    def populate_extension_columns[*Ts](
        stmt: "Select[tuple[*Ts]]", base_model: type[models.Base], composed_model: type[models.Base], info: Info
    ) -> "Select[tuple[*Ts]]":
        """
        Let the extensions populate the extra SQL-backed columns they declared on `composed_model` (see
        GraphQLContribution.populate_sqlalchemy_columns), passing the names of the fields selected in the query so they only
        populate what was requested. Skipped entirely on the common path where no extension contributed columns.

        :param stmt: the query the extension columns are populated onto.
        :param base_model: the original SQLAlchemy model of the object type (e.g. `models.Resource`).
        :param composed_model: the model actually selected by the query: a subclass of `base_model` carrying the
            extensions' extra columns, or `base_model` itself when no extension contributed columns (in which case
            this is a no-op).
        :param info: the Strawberry resolver info, used to determine which fields were selected in the query.
        """
        if composed_model is base_model:
            return stmt
        requested_fields = {to_snake_case(name) for name in get_selected_field_names(info)}
        for contribution in extension_contributions.get(graphql_type_name(base_model), []):
            stmt = contribution.populate_sqlalchemy_columns(stmt, composed_model, requested_fields)
        return stmt

    built_types = {
        graphql_type_name(base_model): build_output_type(base_model, core_mixin)
        for base_model, core_mixin in REGISTRABLE_MODELS.items()
    }
    environment_model, Environment = built_types["Environment"]
    notification_model, Notification = built_types["Notification"]
    resource_model, Resource = built_types["Resource"]

    # Compose the `resources` filter input type from core's filter and the extensions' contributed filters. It is built
    # by multiple inheritance so the resulting GraphQL input exposes the union of all their fields; the resolver
    # decomposes a received value back into one instance per component (see `resource_filter_components`).
    resource_filter_components = get_resource_filter_components(
        extension_contributions.get(graphql_type_name(models.Resource), [])
    )
    composed_resource_filter: type = strawberry.input(
        dataclasses.dataclass(kw_only=True)(type("ResourceFilter", resource_filter_components, {}))
    )

    class CustomInfo(Info):
        @property
        def context(self) -> ContextType:  # type: ignore[type-var]
            return typing.cast(ContextType, {"sqlalchemy_loader": loader, "compiler_service": context.compiler_service})

    @strawberry.type
    class Query:
        @strawberry.field(description="Fetches a paginated list of environments")
        async def environments(
            self,
            info: CustomInfo,
            first: typing.Optional[int] = strawberry.UNSET,
            after: typing.Optional[str] = strawberry.UNSET,
            last: typing.Optional[int] = strawberry.UNSET,
            before: typing.Optional[str] = strawberry.UNSET,
            filter: typing.Optional[EnvironmentFilter] = strawberry.UNSET,
            order_by: typing.Optional[Sequence[EnvironmentOrder]] = strawberry.UNSET,
        ) -> CustomListConnection[Environment]:
            stmt = select(environment_model)
            stmt = populate_extension_columns(stmt, models.Environment, environment_model, info)
            stmt = add_filter_and_sort(
                stmt, EnvironmentOrder.default_order(), [filter] if is_provided(filter) else [], order_by
            )
            return await get_connection(
                stmt, info=info, model="Environment", first=first, after=after, last=last, before=before
            )

        @strawberry.field(description="Fetches a paginated list of notifications")
        async def notifications(
            self,
            info: CustomInfo,
            filter: NotificationFilter,
            first: typing.Optional[int] = strawberry.UNSET,
            after: typing.Optional[str] = strawberry.UNSET,
            last: typing.Optional[int] = strawberry.UNSET,
            before: typing.Optional[str] = strawberry.UNSET,
            order_by: typing.Optional[Sequence[NotificationOrder]] = strawberry.UNSET,
        ) -> CustomListConnection[Notification]:
            stmt = select(notification_model)
            stmt = populate_extension_columns(stmt, models.Notification, notification_model, info)
            stmt = add_filter_and_sort(stmt, NotificationOrder.default_order(), [filter], order_by)
            return await get_connection(
                stmt, info=info, model="Notification", first=first, after=after, last=last, before=before
            )

        @strawberry.field(description="Fetches a paginated list of resources")
        async def resources(
            self,
            info: CustomInfo,
            # The declared type is CoreResourceFilter (so filter.<core field> stays typed), but the GraphQL input
            # the user actually gets is the composed type carrying core + extension fields.
            filter: typing.Annotated[CoreResourceFilter, strawberry.argument(graphql_type=composed_resource_filter)],
            first: typing.Optional[int] = strawberry.UNSET,
            after: typing.Optional[str] = strawberry.UNSET,
            last: typing.Optional[int] = strawberry.UNSET,
            before: typing.Optional[str] = strawberry.UNSET,
            order_by: typing.Optional[Sequence[ResourceOrder]] = strawberry.UNSET,
        ) -> CustomListConnection[Resource]:
            if is_provided(filter.model_version) and is_provided(filter.is_orphan):
                raise Exception("is_orphan cannot be provided when filtering by model_version")

            # Logic based on src/inmanta/data/dataview.py::ResourceView
            # We select `resource_model` (a subclass of models.Resource carrying the extensions' extra columns when
            # there are any, models.Resource otherwise) so each row is a single ORM object that can carry them.
            stmt = select(resource_model).join(
                models.ResourcePersistentState,
                and_(
                    models.Resource.resource_id == models.ResourcePersistentState.resource_id,
                    models.Resource.environment == models.ResourcePersistentState.environment,
                ),
            )

            # Decompose the composed ResourceFilter into one instance per component (core + each extension). Each
            # component's fields are read off the received filter, and at most one component may take over version
            # selection (`handles_version`); core does it by default.
            resource_filter_instances: list[ResourceFilterABC] = []
            version_handler: ResourceFilterABC | None = None
            for filter_type in resource_filter_components:
                filter_fields = {field.name: getattr(filter, field.name) for field in dataclasses.fields(filter_type)}
                filter_instance = filter_type(**filter_fields)
                resource_filter_instances.append(filter_instance)
                if filter_instance.handles_version():
                    if version_handler is not None:
                        raise Exception("Only one extension can determine version logic.")
                    version_handler = filter_instance

            # True when a component actively took over version selection (core via is_orphan/model_version, or an
            # extension) rather than the plain default of "latest scheduled version + orphans".
            custom_version_selection = version_handler is not None
            if version_handler is None:
                version_handler = next(i for i in resource_filter_instances if isinstance(i, CoreResourceFilter))
            stmt = version_handler.apply_version_filter(stmt)

            stmt = populate_extension_columns(stmt, models.Resource, resource_model, info)
            stmt = add_filter_and_sort(stmt, ResourceOrder.default_order(), resource_filter_instances, order_by)
            count_stmt: Select[tuple[int]] | None
            if is_provided(filter.purged) or is_provided(filter.model_version) or custom_version_selection:
                # These filters are not (only) applied on ResourcePersistentState, so the more efficient count below
                # would not match; fall back to counting the actual (version-aware) resource query.
                count_stmt = None
            else:
                # more efficient count statement that doesn't require joining on resource
                count_stmt = add_filter_and_sort(
                    select(func.count()).select_from(models.ResourcePersistentState), {}, resource_filter_instances
                )
            return await get_connection(
                stmt, info=info, model="Resource", first=first, after=after, last=last, before=before, count_stmt=count_stmt
            )

        @strawberry.field(description="Fetches a summary of the state of all resources in a specific environment")
        async def resource_summary(self, info: CustomInfo, environment: str) -> ComposedResourceSummary:
            results = await data.Resource.get_composed_resource_summary(environment)
            return ComposedResourceSummary(
                total_count=results.total_count,
                last_handler_run=cast(JSON, results.last_handler_run),
                blocked=cast(JSON, results.blocked),
                compliance=cast(JSON, results.compliance),
                is_deploying=cast(JSON, results.is_deploying),
            )

    return strawberry.Schema(query=Query, config=StrawberryConfig(info_class=CustomInfo))
