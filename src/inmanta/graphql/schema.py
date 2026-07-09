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
from sqlalchemy import Boolean, ColumnElement, Select, UnaryExpression, and_, asc, desc, func, not_, select
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

    3) The `StrawberryFilter` child class for our strawberry model, declared as the type's "core filter" i.e.
        ```
            @strawberry.input
            class CoreEnvironmentFilter(StrawberryFilter):
                id: typing.Optional[str] = strawberry.UNSET
        ```
        `get_schema` composes this core filter with any extension-contributed filters (see `GraphQLContribution` and
        `build_composed_filter_input`) into the user-facing `EnvironmentFilter` input; the resolver decomposes a
        received value back into its components with `decompose_filter` and applies each.
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
        Returns the provided filter fields in dict form, to feed to the SQLAlchemy query as an exact-match filter.
        Fields left UNSET are skipped (not filtered on) -- this is what lets a filter compose with others that carry
        their own fields (see `decompose_filter`).
        This is only used for simple filters i.e. exact match on the same table.
        """
        return {key: value for key, value in self.__dict__.items() if value is not strawberry.UNSET}

    def apply_filter[*Ts](self, stmt: Select[tuple[*Ts]]) -> Select[tuple[*Ts]]:
        """
        Applies the filters to the given query.
        """
        return stmt.filter_by(**self.get_filter_dict())

    def validate_filter(self) -> None:
        """
        Validate the provided filter fields, raising a `ValueError` if they are inconsistent (e.g. two mutually
        exclusive fields are set). Called on every component of a composed filter before it is applied. The default
        accepts everything; override to add component-specific validation.
        """
        return


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


@dataclasses.dataclass(kw_only=True)
@strawberry.input
class CoreEnvironmentFilter(StrawberryFilter):
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


@dataclasses.dataclass(kw_only=True)
@strawberry.input
class CoreNotificationFilter(StrawberryFilter):
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
    `CoreResourceFilter` and each extension's resource filter (contributed via `GraphQLContribution.get_filter_input_class`).
    The version-selection hooks below are specific to resources; other object types' filters compose the same way but
    have no version concept.

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

    def filters_on_resource_table(self) -> bool:
        """
        Return True if this component's `apply_filter` constrains the `Resource` table (`models.Resource`) rather
        than only `ResourcePersistentState`. The `resources` query uses this to decide whether the efficient count
        (which counts `ResourcePersistentState` alone, without joining `Resource`) is valid: it is only used when no
        applied component filters on the `Resource` table.
        """
        return False


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

    def validate_filter(self) -> None:
        # modelVersion returns the resources exactly as they were in that version of the model. The filters below
        # reflect the *current* state of a resource (tracked on ResourcePersistentState, which is not versioned),
        # so combining them with modelVersion would mix a historical snapshot with current state.
        if is_provided(self.model_version):
            current_state_filters = {
                "isOrphan": self.is_orphan,
                "isDeploying": self.is_deploying,
                "blocked": self.blocked,
                "compliance": self.compliance,
                "lastHandlerRun": self.last_handler_run,
            }
            conflicting = [name for name, value in current_state_filters.items() if is_provided(value)]
            if conflicting:
                raise ValueError(
                    "modelVersion cannot be combined with filters on the current resource state: " + ", ".join(conflicting)
                )

    def handles_version(self) -> bool:
        # is_orphan and model_version both control which version(s) of the model are selected, so providing either
        # means core owns version selection.
        return is_provided(self.is_orphan) or is_provided(self.model_version)

    def apply_version_filter[*Ts](self, stmt: Select[tuple[*Ts]]) -> Select[tuple[*Ts]]:
        # Determine which version of the model each resource should be taken from:
        #  - if a specific version was requested, pin every resource set to that version
        #  - otherwise take each resource at the latest scheduled version, except orphaned resources which are
        #    taken at the last version they were present in (orphaned_after).
        #    For non-orphaned resources orphaned_after is NULL, so coalesce falls back to the latest scheduled version.
        version: int | ColumnElement[int]
        if is_provided(self.model_version):
            version = self.model_version
        else:
            # Compute the latest scheduled version once, as a CTE, instead of inlining the subquery in the join
            # condition below, so it is not (re-)evaluated per candidate row.
            latest_scheduled_version = (
                select(models.Scheduler.last_processed_model_version.label("version"))
                .where(models.Scheduler.environment == self.environment)
                .cte()
            )
            version = func.coalesce(
                models.ResourcePersistentState.orphaned_after,
                select(latest_scheduled_version.c.version).scalar_subquery(),
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

    def filters_on_resource_table(self) -> bool:
        # `purged` is the only core filter applied on the `Resource` table (`attributes`); every other core filter
        # constrains `ResourcePersistentState`.
        return is_provided(self.purged)


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

    :param stmt: the query to add the filter and sorting to.
    :param default_sorting: the sorting to apply for each key not already covered by `order_by`.
    :param filter: the filter components to apply. A single query can have several components: the `resources` query
        composes core and extension filters, while the other queries pass a single (or no) filter.
    :param order_by: the sorting requested by the user, taking precedence over `default_sorting` for the same key.
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
    def get_filter_input_class(cls) -> "type[StrawberryFilter] | None":
        """
        Return a `@strawberry.input` filter class whose fields are composed into the target type's filter input,
        letting this extension filter that type's query on its own fields (its `apply_filter` runs alongside core's).
        Return None (the default) to contribute no filter fields.

        The class must be compatible with the target type's core filter, since the two are composed by multiple
        inheritance: for `models.Resource` that means a `ResourceFilterABC` subclass (which may also take over version
        selection via `handles_version` / `apply_version_filter`); for other types, a `StrawberryFilter` subclass.
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


def get_filter_components(
    core_filter: type[StrawberryFilter],
    contributions: Sequence[type[GraphQLContribution]],
) -> tuple[type[StrawberryFilter], ...]:
    """
    Return the filter components that compose an object type's filter input type: the type's `core_filter` followed by
    every extension-contributed filter class. `build_composed_filter_input` builds the composed input from these by multiple
    inheritance, and each query's resolver decomposes the received filter back
    into one instance per component (see `decompose_filter`) to apply them.

    :param core_filter: the core filter class of the object type (e.g. `CoreResourceFilter`).
    :param contributions: the extension contributions that target the same object type.
    """
    extension_filters: list[type[StrawberryFilter]] = [
        cls for c in contributions if (cls := c.get_filter_input_class()) is not None
    ]
    return (core_filter, *extension_filters)


def build_composed_filter_input(
    type_name: str,
    core_filter: type[StrawberryFilter],
    contributions: Sequence[type[GraphQLContribution]],
) -> tuple[tuple[type[StrawberryFilter], ...], type]:
    """
    Build the filter input type for an object type, composed of its core filter and the extensions' contributed
    filters. The components are merged by multiple inheritance into a single `@strawberry.input` named `{type_name}Filter`.

    :param type_name: the name of the object type being built (e.g. "Resource").
    :param core_filter: the core filter class of the object type (e.g. `CoreResourceFilter`).
    :param contributions: the extension contributions that target this type.
    """
    components = get_filter_components(core_filter, contributions)
    # Guard against multiple components having the same field that is not shared
    # __annotations__ is used because it doesn't contain the fields of the parent class so those are excluded for the comparison
    seen_fields: set[str] = set()
    for component in components:
        for field_name in component.__dict__.get("__annotations__", {}):
            if field_name in seen_fields:
                raise Exception(f"{field_name} defined more than once in {type_name} filters.")
            seen_fields.add(field_name)
    composed = cast(
        type,
        strawberry.input(dataclasses.dataclass(kw_only=True)(type(f"{type_name}Filter", components, {}))),
    )
    return components, composed


def decompose_filter[F: StrawberryFilter](filter: object, components: tuple[type[F], ...]) -> list[F]:
    """
    Split a composed filter value back into one instance per component, reading each component's fields off the composed value.
    This lets every component apply its own `apply_filter` on just its own fields.

    :param filter: the composed filter value received by the resolver.
    :param components: the filter components the composed type was built from.
    """
    decomposed: list[F] = []
    for component in components:
        component_fields = dataclasses.fields(component)  # type: ignore[arg-type]
        decomposed.append(component(**{field.name: getattr(filter, field.name) for field in component_fields}))
    return decomposed


@dataclasses.dataclass(frozen=True)
class RegistrableGraphQLType:
    """
    The core building blocks of an object type that extensions can contribute to (see `GraphQLContribution`):
    the mixin carrying its core output fields and the class carrying its core filter fields. `get_schema` composes
    each with the registered contributions to build the object type's output type and filter input type.
    """

    core_mixin: type
    core_filter: type[StrawberryFilter]


# The object types extensions can register GraphQL contributions for (see GraphQLContribution), mapping each SQLAlchemy
# model to its core building blocks. `get_schema` composes each of these from the core building blocks and the
# registered contributions; registrations for any other model are rejected.
REGISTRABLE_MODELS: "Mapping[type[models.Base], RegistrableGraphQLType]" = {
    models.Resource: RegistrableGraphQLType(core_mixin=CoreResourceMixin, core_filter=CoreResourceFilter),
    models.Environment: RegistrableGraphQLType(core_mixin=CoreEnvironmentMixin, core_filter=CoreEnvironmentFilter),
    models.Notification: RegistrableGraphQLType(core_mixin=CoreNotificationMixin, core_filter=CoreNotificationFilter),
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

    # Build each registrable object type's output type and filter input.
    built_types: dict[GraphQLTypeName, tuple[type[models.Base], type]] = {}
    built_filters: dict[GraphQLTypeName, tuple[tuple[type[StrawberryFilter], ...], type]] = {}
    for base_model, registrable in REGISTRABLE_MODELS.items():
        type_name = graphql_type_name(base_model)
        contributions = extension_contributions.get(type_name, [])
        built_types[type_name] = build_output_type(base_model, registrable.core_mixin)
        built_filters[type_name] = build_composed_filter_input(type_name, registrable.core_filter, contributions)

    environment_model, Environment = built_types[graphql_type_name(models.Environment)]
    notification_model, Notification = built_types[graphql_type_name(models.Notification)]
    resource_model, Resource = built_types[graphql_type_name(models.Resource)]
    environment_filter_components, EnvironmentFilter = built_filters[graphql_type_name(models.Environment)]
    notification_filter_components, NotificationFilter = built_filters[graphql_type_name(models.Notification)]
    resource_filter_components, ResourceFilter = built_filters[graphql_type_name(models.Resource)]

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
            filter: typing.Annotated[
                typing.Optional[CoreEnvironmentFilter], strawberry.argument(graphql_type=typing.Optional[EnvironmentFilter])
            ] = strawberry.UNSET,
            order_by: typing.Optional[Sequence[EnvironmentOrder]] = strawberry.UNSET,
        ) -> CustomListConnection[Environment]:
            stmt = select(environment_model)
            stmt = populate_extension_columns(stmt, models.Environment, environment_model, info)
            filters = decompose_filter(filter, environment_filter_components) if is_provided(filter) else []
            for filter_component in filters:
                filter_component.validate_filter()
            stmt = add_filter_and_sort(stmt, EnvironmentOrder.default_order(), filters, order_by)
            return await get_connection(
                stmt, info=info, model="Environment", first=first, after=after, last=last, before=before
            )

        @strawberry.field(description="Fetches a paginated list of notifications")
        async def notifications(
            self,
            info: CustomInfo,
            filter: typing.Annotated[CoreNotificationFilter, strawberry.argument(graphql_type=NotificationFilter)],
            first: typing.Optional[int] = strawberry.UNSET,
            after: typing.Optional[str] = strawberry.UNSET,
            last: typing.Optional[int] = strawberry.UNSET,
            before: typing.Optional[str] = strawberry.UNSET,
            order_by: typing.Optional[Sequence[NotificationOrder]] = strawberry.UNSET,
        ) -> CustomListConnection[Notification]:
            stmt = select(notification_model)
            stmt = populate_extension_columns(stmt, models.Notification, notification_model, info)
            filters = decompose_filter(filter, notification_filter_components)
            for filter_component in filters:
                filter_component.validate_filter()
            stmt = add_filter_and_sort(stmt, NotificationOrder.default_order(), filters, order_by)
            return await get_connection(
                stmt, info=info, model="Notification", first=first, after=after, last=last, before=before
            )

        @strawberry.field(description="Fetches a paginated list of resources")
        async def resources(
            self,
            info: CustomInfo,
            filter: typing.Annotated[CoreResourceFilter, strawberry.argument(graphql_type=ResourceFilter)],
            first: typing.Optional[int] = strawberry.UNSET,
            after: typing.Optional[str] = strawberry.UNSET,
            last: typing.Optional[int] = strawberry.UNSET,
            before: typing.Optional[str] = strawberry.UNSET,
            order_by: typing.Optional[Sequence[ResourceOrder]] = strawberry.UNSET,
        ) -> CustomListConnection[Resource]:
            stmt = select(resource_model).join(
                models.ResourcePersistentState,
                and_(
                    models.Resource.resource_id == models.ResourcePersistentState.resource_id,
                    models.Resource.environment == models.ResourcePersistentState.environment,
                ),
            )

            # Decompose the composed ResourceFilter into one instance per component (core + each extension). Every
            # resource filter component is a ResourceFilterABC, and at most one may take over version selection
            # Core does it by default.
            resource_filter_instances = cast(list[ResourceFilterABC], decompose_filter(filter, resource_filter_components))
            version_handler: ResourceFilterABC | None = None
            filters_on_resource_table: bool = False
            for filter_instance in resource_filter_instances:
                filter_instance.validate_filter()
                if filter_instance.handles_version():
                    if version_handler is not None:
                        raise ValueError("Only one extension can determine version logic.")
                    version_handler = filter_instance
                if filter_instance.filters_on_resource_table():
                    filters_on_resource_table = True

            # True when a component actively took over version selection
            # rather than the plain default of "latest scheduled version + orphans".
            custom_version_selection = version_handler is not None
            if version_handler is None:
                version_handler = next(i for i in resource_filter_instances if isinstance(i, CoreResourceFilter))
            stmt = version_handler.apply_version_filter(stmt)

            stmt = populate_extension_columns(stmt, models.Resource, resource_model, info)
            stmt = add_filter_and_sort(stmt, ResourceOrder.default_order(), resource_filter_instances, order_by)
            count_stmt: Select[tuple[int]] | None
            # The efficient count below only selects from ResourcePersistentState, so it is only valid when the row
            # set it counts matches the real query: no component may change the version selection, and no component's
            # apply_filter may constrain the Resource table.
            # Otherwise, fall back to counting the actual (version-aware) resource query.
            if custom_version_selection or filters_on_resource_table:
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
