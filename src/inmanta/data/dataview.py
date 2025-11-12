"""
Copyright 2022 Inmanta

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

import abc
import json
import urllib.parse
from abc import ABC
from collections.abc import Sequence
from datetime import datetime
from typing import Generic, Mapping, Optional, TypeVar, Union, cast
from uuid import UUID

from asyncpg import Record

import inmanta.data
from inmanta import const, data
from inmanta.data import (
    APILIMIT,
    PRIMITIVE_SQL_TYPES,
    Agent,
    AgentOrder,
    CompileReportOrder,
    ConfigurationModel,
    DatabaseOrderV2,
    DesiredStateVersionOrder,
    DiscoveredResourceOrder,
    FactOrder,
    InvalidQueryParameter,
    InvalidSort,
    Notification,
    NotificationOrder,
    PagingOrder,
    Parameter,
    ParameterOrder,
    QueryFilter,
    Resource,
    ResourceAction,
    ResourceHistoryOrder,
    ResourceLogOrder,
    ResourceStatusOrder,
    Scheduler,
    SimpleQueryBuilder,
    VersionedResourceOrder,
    model,
)
from inmanta.data.model import (
    BaseModel,
    CompileReport,
    DesiredStateLabel,
    DesiredStateVersion,
    Fact,
    LatestReleasedResource,
    PagingBoundaries,
    ResourceHistory,
    ResourceLog,
)
from inmanta.protocol.exceptions import BadRequest
from inmanta.protocol.return_value_meta import ReturnValueWithMeta
from inmanta.resources import Id
from inmanta.server import config as opt
from inmanta.server.validate_filter import (
    BooleanEqualityFilter,
    BooleanIsNotNullFilter,
    CombinedContainsFilterResourceState,
    ContainsFilter,
    ContainsFilterResourceAction,
    ContainsPartialFilter,
    DateRangeFilter,
    Filter,
    FilterValidator,
    IntRangeFilter,
    InvalidFilter,
    LogLevelFilter,
)
from inmanta.types import JsonType, ResourceIdStr, ResourceVersionIdStr, SimpleTypes
from inmanta.util import datetime_iso_format

T_ORDER = TypeVar("T_ORDER", bound=DatabaseOrderV2)
T_DTO = TypeVar("T_DTO", bound=BaseModel)


class RequestedPagingBoundaries:
    """
    Represents the lower and upper bounds that the user requested for the paging boundaries, if any.

    Boundary values represent min and max values, regardless of sorting direction (ASC or DESC), e.g
    - ASC sorting based on next links -> a page is requested for which all elements are > (start,first_id)
    - ASC sorting based on prev links -> a page is requested for which all elements are < (end,last_id)
    - DESC sorting based on next links -> a page is requested for which all elements are < (end,last_id)
    - DESC sorting based on prev links -> a page is requested for which all elements are > (start,first_id)

    So, while the names "start" and "end" might seem to indicate "left" and "right" of the page, they actually mean "lowest" and
    "highest".

    :param start: min boundary value (exclusive) for the requested page for the primary sort column.
    :param end: max boundary value (exclusive) for the requested page for the primary sort column.
    :param first_id: min boundary value (exclusive) for the requested page for the secondary sort column, if there is one.
    :param last_id: max boundary value (exclusive) for the requested page for the secondary sort column, if there is one.
    """

    def __init__(
        self,
        start: Optional[PRIMITIVE_SQL_TYPES],
        end: Optional[PRIMITIVE_SQL_TYPES],
        first_id: Optional[PRIMITIVE_SQL_TYPES],
        last_id: Optional[PRIMITIVE_SQL_TYPES],
    ) -> None:
        self.start = start
        self.end = end
        self.first_id = first_id
        self.last_id = last_id

    def validate(
        self,
    ) -> None:
        start = self.start
        end = self.end
        first_id = self.first_id
        last_id = self.last_id
        if (start is not None) and (end is not None):
            raise InvalidQueryParameter(
                f"Only one of start and end parameters is allowed at the same time. Received start: {start}, end: {end}"
            )
        if (first_id is not None) and (last_id is not None):
            raise InvalidQueryParameter(
                f"Only one of first_id and last_id parameters is allowed at the same time. "
                f"Received first_id: {first_id}, last_id: {last_id}"
            )

        if self.has_start() and self.has_end():
            raise InvalidQueryParameter(
                f"Start and end parameters can not be set at the same time: "
                f"Received first_id: {first_id}, last_id: {last_id}, start: {start}, end: {end}"
            )

    def has_start(self) -> bool:
        return (self.start is not None) or (self.first_id is not None)

    def has_end(self) -> bool:
        return (self.end is not None) or (self.last_id is not None)

    def get_empty_page_boundaries(self) -> PagingBoundaries:
        """
        Return the virtual paging boundaries that corresponds to the boundaries of an empty page response for this request.

        Concretely, this means swapping start and end, because the semantics of PagingBoundaries are opposite those of this
        class: PagingBoundaries' boundary values map to RequestedPagingBoundaries` boundary values for the next and previous
        pages, e.g. requested max = requested min of next page and vice versa.

        Known-issue: This method contains a potential off-by-one error here because both classes are exclusive of the boundary
        values. Issue: https://github.com/inmanta/inmanta-core/issues/7898#issuecomment-2404322678
        """
        return PagingBoundaries(
            start=self.end,
            first_id=self.last_id,
            end=self.start,
            last_id=self.first_id,
        )


class PagingMetadata:
    def __init__(self, total: int, before: int, after: int, page_size: int) -> None:
        self.total = total
        self.before = before
        self.after = after
        self.page_size = page_size

    def to_dict(self) -> dict[str, int]:
        return {
            "total": self.total,
            "before": self.before,
            "after": self.after,
            "page_size": self.page_size,
        }


class DataView(FilterValidator, Generic[T_ORDER, T_DTO], ABC):
    def __init__(
        self,
        order: T_ORDER,
        limit: Optional[int] = None,
        first_id: Optional[PRIMITIVE_SQL_TYPES] = None,
        last_id: Optional[PRIMITIVE_SQL_TYPES] = None,
        start: Optional[PRIMITIVE_SQL_TYPES] = None,
        end: Optional[PRIMITIVE_SQL_TYPES] = None,
        filter: Optional[Mapping[str, Sequence[str]]] = None,
    ) -> None:
        """
        All boundary values for paging are exclusive, i.e. the returned page will contain only values strictly larger/smaller
        than the boundary value. "start", "first", "end" and "last" are poorly named: they imply to be ordering-aware, while
        they're actually only about the requested page containing "larger" or "smaller" values respectively, regardless of
        the requested order.

        :param first_id: secondary boundary value for min bound. If not None, boundary is `> (start, first_id)`.
        :param last_id: secondary boundary value for max bound. If not None, boundary is `< (end, last_id)`.
        :param start: primary boundary value for min bound. If first_id is None, boundary is `> start`.
        :param end: primary boundary value for max bound. If last_id is None, boundary is `< end`.
        """
        self.limit = self.validate_limit(limit)
        self.raw_filter = filter or {}
        self.filter: dict[str, QueryFilter] = self.process_filters(filter)
        self.order = order
        self.requested_page_boundaries = RequestedPagingBoundaries(start, end, first_id, last_id)
        self.requested_page_boundaries.validate()

    @abc.abstractmethod
    def get_base_url(self) -> str:
        """
        Return the base URL used to construct the paging links

        e.g. "/api/v2/resource"
        """

    def get_extra_url_parameters(self) -> dict[str, str]:
        """
        Return additional URL query parameters required to construct the paging links
        """
        return {}

    async def get_data(self) -> tuple[Sequence[T_DTO], PagingBoundaries]:
        query_builder = self.get_base_query()

        # In this method, we use `data.Resource`
        # we need the generic functionality of `data.BaseDocument`
        # But that one doesn't actually hold a connection, as it is abstract

        # Project
        query_builder = query_builder.filter(
            *data.Resource.get_composed_filter_with_query_types(
                offset=query_builder.offset, col_name_prefix=None, **self.filter
            )
        )
        query_builder = self.clip_to_page(query_builder)
        sql_query, values = query_builder.build()

        records = await data.Resource.select_query(sql_query, values, no_obj=True)
        dtos = self.construct_dtos(records)

        paging_boundaries = (
            self.order.get_paging_boundaries(dict(records[0]), dict(records[-1]))
            if dtos
            else self.requested_page_boundaries.get_empty_page_boundaries()
        )
        return dtos, paging_boundaries

    @abc.abstractmethod
    def construct_dtos(self, records: Sequence[Record]) -> Sequence[T_DTO]:
        """
        Convert the sequence of records into a sequence of DTO's
        """

    @abc.abstractmethod
    def get_base_query(self) -> SimpleQueryBuilder:
        """
        Return the base query to get the data.

        Must contain select, from and where clause if specific filtering is required
        """

    def get_base_query_for_page_count(self) -> SimpleQueryBuilder:
        """
        Override this method to use a different query than returned by get_base_query()
        to calculate the page count for a certain page.
        """
        return self.get_base_query()

    @property
    @abc.abstractmethod
    def allowed_filters(self) -> dict[str, type[Filter]]:
        """
        Return the specification of the allowed filters, see FilterValidator
        """

    def clip_to_page(self, query_builder: SimpleQueryBuilder) -> SimpleQueryBuilder:
        """
        Update the query builder to constrain it to the page boundaries, order and size
        """
        order = self.order.get_order()
        backward_paging: bool = (order == PagingOrder.ASC and self.requested_page_boundaries.has_end()) or (
            order == PagingOrder.DESC and self.requested_page_boundaries.has_start()
        )

        return (
            query_builder.filter(
                *self.order.as_filter(
                    query_builder.offset,
                    self.requested_page_boundaries.start,
                    self.requested_page_boundaries.first_id,
                    start=True,
                )
            )
            .filter(
                *self.order.as_filter(
                    query_builder.offset,
                    self.requested_page_boundaries.end,
                    self.requested_page_boundaries.last_id,
                    start=False,
                )
            )
            .order_and_limit(self.order, self.limit, backward_paging)
        )

    async def execute(self) -> ReturnValueWithMeta[Sequence[T_DTO]]:
        """
        Main entry point:
        - get the data from the DB
        - get page counts
        - format paging links

        :return: Complete API ReturnValueWithMeta ready to go out
        """
        try:
            dtos, paging_boundaries = await self.get_data()
            metadata = await self._get_page_count(paging_boundaries)
            links = await self.prepare_paging_links(paging_boundaries, metadata)
            return ReturnValueWithMeta(response=dtos, links=links if links else {}, metadata=metadata.to_dict())
        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e

    # Paging helpers

    async def _get_page_count(self, bounds: PagingBoundaries) -> PagingMetadata:
        """
        Construct the page counts,

        either from the PagingBoundaries if we have a valid page,
        or from the RequestedPagingBoundaries if we got an empty page
        """
        query_builder = self.get_base_query_for_page_count()

        query_builder = query_builder.filter(
            *data.BaseDocument.get_composed_filter_with_query_types(
                offset=query_builder.offset, col_name_prefix=None, **self.filter
            )
        )

        order = self.order.get_order()
        reversed = order == PagingOrder.DESC

        end, start, last_id, first_id = bounds.end, bounds.start, bounds.last_id, bounds.first_id

        if reversed:
            end, start = start, end
            last_id, first_id = first_id, last_id

        values = query_builder.values
        after_filter_statements, after_values = self.order.as_filter(len(values) + 1, start, first_id, start=not reversed)
        values.extend(after_values)
        after_filter = data.BaseDocument._join_filter_statements(after_filter_statements)

        before_filter_statements, before_values = self.order.as_filter(len(values) + 1, end, last_id, start=reversed)
        values.extend(before_values)
        before_filter = data.BaseDocument._join_filter_statements(before_filter_statements)

        # If the currently requested page was empty,
        # we are working from RequestedPagingBoundaries instead of PagingBoundaries
        # If the RequestedPagingBoundaries has only nulls, we are not paging and the total count is 0
        # If the RequestedPagingBoundaries has one pair of nulls,
        #   we are paging but the current page is empty and so are the next ones
        # the `as_filter` method will return empty if the input is null
        # so we can conclude that the value for an empty filter is always 0

        if not before_filter and not after_filter:
            # Table is empty
            # Don't even make the query
            return PagingMetadata(
                total=0,
                before=0,
                after=0,
                page_size=self.limit,
            )

        select_clause = (
            "SELECT COUNT(*) as count_total"
            + (f", COUNT(*) filter ({before_filter}) as count_before" if before_filter else "")
            + (f", COUNT(*) filter ({after_filter}) as count_after " if after_filter else "")
        )

        query_builder = query_builder.select(select_clause)

        sql_query, values = query_builder.build()
        result = await data.Resource.select_query(sql_query, values, no_obj=True)
        result = cast(list[Record], result)
        if not result:
            raise InvalidQueryParameter("Could not determine page bounds")
        return PagingMetadata(
            total=cast(int, result[0]["count_total"]),
            before=cast(int, result[0].get("count_before", 0)),
            after=cast(int, result[0].get("count_after", 0)),
            page_size=self.limit,
        )

    async def prepare_paging_links(
        self,
        paging_boundaries: PagingBoundaries,
        meta: PagingMetadata,
    ) -> dict[str, str]:
        """
        Construct the paging links
        """
        links = {}

        url_query_params: dict[str, Optional[Union[SimpleTypes, Sequence[str]]]] = {
            "limit": self.limit,
            "sort": str(self.order),
        }

        for key, value in self.raw_filter.items():
            if value is not None:
                url_query_params[f"filter.{key}"] = value

        url_query_params.update(self.get_extra_url_parameters())
        base_url = self.get_base_url()

        def value_to_string(value: Union[str, int, UUID, datetime]) -> str:
            if isinstance(value, datetime):
                # Accross API boundaries, all naive datetime instances are assumed UTC.
                # Returns ISO timestamp.
                return datetime_iso_format(value, tz_aware=opt.server_tz_aware_timestamps.get())
            return str(value)

        def make_link(**args: Optional[Union[str, int, UUID, datetime]]) -> str:
            params = url_query_params.copy()
            params.update({k: value_to_string(v) for k, v in args.items() if v is not None})
            return f"{base_url}?{urllib.parse.urlencode(params, doseq=True)}"

        link_with_end = make_link(
            end=paging_boundaries.end,
            last_id=paging_boundaries.last_id,
        )
        link_with_start = make_link(
            start=paging_boundaries.start,
            first_id=paging_boundaries.first_id,
        )

        if meta.after > 0:
            if self.order.get_order() == "DESC":
                links["next"] = link_with_end
            else:
                links["next"] = link_with_start

        if meta.before > 0:
            if self.order.get_order() == "DESC":
                links["prev"] = link_with_start
            else:
                links["prev"] = link_with_end
            # First page
            links["first"] = make_link()

        # Same page
        links["self"] = make_link(
            first_id=self.requested_page_boundaries.first_id,
            start=self.requested_page_boundaries.start,
        )
        # TODO: last links
        return links

    def validate_limit(self, limit: Optional[int]) -> int:
        if limit is None:
            return APILIMIT
        if limit > APILIMIT:
            raise BadRequest(f"limit parameter can not exceed {APILIMIT}, got {limit}.")
        return limit


class ResourceView(DataView[ResourceStatusOrder, model.LatestReleasedResource]):
    def __init__(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        first_id: Optional[ResourceVersionIdStr] = None,
        last_id: Optional[ResourceVersionIdStr] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        filter: Optional[dict[str, list[str]]] = None,
        sort: str = "resource_type.desc",
        deploy_summary: bool = False,
    ) -> None:
        super().__init__(
            order=ResourceStatusOrder.parse_from_string(sort),
            limit=limit,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            filter=filter,
        )
        self.environment = env
        self.deploy_summary = deploy_summary

        # Rewrite the filter to special case orphan handling
        # We handle the non-orphan case by changing the query, so we don't need the filter
        # This doesn't affect the paging links, as they use the raw filter

        status_filter_type, status_filter_fields = self.filter.get("status", (None, {}))
        assert status_filter_type is None or status_filter_type == inmanta.data.QueryType.COMBINED
        assert isinstance(status_filter_fields, dict)
        self.drop_orphans = "orphaned" in status_filter_fields.get(inmanta.data.QueryType.NOT_CONTAINS, []) or (
            "orphaned" not in status_filter_fields.get(inmanta.data.QueryType.CONTAINS, ["orphaned"])
        )

        if self.drop_orphans:
            # clean filter for orphans
            try:
                status_filter_fields.get(inmanta.data.QueryType.NOT_CONTAINS, []).remove("orphaned")
                if not status_filter_fields.get(inmanta.data.QueryType.NOT_CONTAINS, []):
                    del status_filter_fields[inmanta.data.QueryType.NOT_CONTAINS]
                if not status_filter_fields:
                    del self.filter["status"]
            except ValueError:
                pass

    @property
    def allowed_filters(self) -> dict[str, type[Filter]]:
        return {
            "resource_type": ContainsPartialFilter,
            "agent": ContainsPartialFilter,
            "resource_id_value": ContainsPartialFilter,
            "status": CombinedContainsFilterResourceState,
        }

    def get_base_url(self) -> str:
        return "/api/v2/resource"

    def get_extra_url_parameters(self) -> dict[str, str]:
        return {"deploy_summary": str(self.deploy_summary)}

    def get_base_query(self) -> SimpleQueryBuilder:
        new_query_builder = SimpleQueryBuilder(
            select_clause="SELECT *",
            prelude=f"""
               WITH latest_version AS (
                    SELECT MAX(public.configurationmodel.version) as version
                    FROM public.configurationmodel
                    WHERE public.configurationmodel.released=TRUE AND environment=$1
                ), versioned_resource_state AS (
                    SELECT
                        rps.*,
                        CASE
                            -- try the cheap, trivial option first because the lookup has a big performance impact
                            WHEN EXISTS (
                                SELECT 1
                                FROM resource AS r
                                WHERE r.environment = rps.environment AND r.resource_id = rps.resource_id AND r.model = (
                                    SELECT version FROM latest_version
                                )
                            ) THEN (SELECT version FROM latest_version)
                            -- only if the resource does not exist in the latest released version, search for the latest
                            -- version it does exist in
                            ELSE (
                                SELECT MAX(r.model)
                                FROM resource AS r
                                JOIN configurationmodel AS m
                                    ON r.environment = m.environment AND r.model = m.version AND m.released = TRUE
                                WHERE r.environment = rps.environment AND r.resource_id = rps.resource_id
                            )
                        END AS version
                    FROM resource_persistent_state AS rps
                    WHERE rps.environment = $1
                ), result AS (
                    SELECT
                        rps.resource_id,
                        r.attributes,
                        rps.resource_type,
                        rps.agent,
                        rps.resource_id_value,
                        r.model,
                        rps.environment,
                        (
                            CASE
                                -- The resource_persistent_state.last_non_deploying_status column is only populated for
                                -- actual deployment operations to prevent locking issues. This case-statement calculates
                                -- the correct state from the combination of the resource table and the
                                -- resource_persistent_state table.
                                WHEN r.model < (SELECT version FROM latest_version)
                                    THEN 'orphaned'
                                WHEN r.status::text IN('deploying', 'undefined', 'skipped_for_undefined')
                                    -- The deploying, undefined and skipped_for_undefined states are not tracked in the
                                    -- resource_persistent_state table.
                                    THEN r.status::text
                                WHEN rps.last_deployed_attribute_hash != r.attribute_hash
                                    -- The hash changed since the last deploy -> new desired state
                                    THEN r.status::text
                                    -- No override required, use last known state from actual deployment
                                    ELSE rps.last_non_deploying_status::text
                            END
                        ) as status
                    FROM versioned_resource_state AS rps
            -- LEFT join for trivial `COUNT(*)`. Not applicable when filtering orphans because left table contains orphans.
                    {'' if self.drop_orphans else 'LEFT'} JOIN resource AS r
                        ON r.environment = rps.environment
                          AND r.resource_id = rps.resource_id
           -- shortcut the version selection to the latest one iff we wish to exclude orphans
           -- => no per-resource MAX required + wider index application
                          AND r.model = {'(SELECT version FROM latest_version)' if self.drop_orphans else 'rps.version'}
                    WHERE rps.environment = $1
                )
            """,
            from_clause="FROM result AS r",
            values=[self.environment.id],
        )
        return new_query_builder

    def construct_dtos(self, records: Sequence[Record]) -> Sequence[model.LatestReleasedResource]:
        dtos: Sequence[LatestReleasedResource] = [
            model.LatestReleasedResource(
                resource_id=resource["resource_id"],
                resource_version_id=resource["resource_id"] + ",v=" + str(resource["model"]),
                id_details=data.Resource.get_details_from_resource_id(resource["resource_id"]),
                status=resource["status"],
                requires=json.loads(resource["attributes"]).get("requires", []),
            )
            for resource in records
            if resource["attributes"]  # filter out bad joins
        ]
        return dtos


class ResourcesInVersionView(DataView[VersionedResourceOrder, model.VersionedResource]):
    def __init__(
        self,
        environment: data.Environment,
        version: int,
        limit: Optional[int] = None,
        filter: Optional[dict[str, list[str]]] = None,
        sort: str = "resource_type.desc",
        first_id: Optional[ResourceVersionIdStr] = None,
        last_id: Optional[ResourceVersionIdStr] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> None:
        super().__init__(
            order=VersionedResourceOrder.parse_from_string(sort),
            limit=limit,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            filter=filter,
        )
        self.environment = environment
        self.version = version

    # Per view config
    def get_base_url(self) -> str:
        return f"/api/v2/desiredstate/{self.version}"

    @property
    def allowed_filters(self) -> dict[str, type[Filter]]:
        return {
            "resource_type": ContainsPartialFilter,
            "agent": ContainsPartialFilter,
            "resource_id_value": ContainsPartialFilter,
        }

    def get_base_query(self) -> SimpleQueryBuilder:
        query_builder = SimpleQueryBuilder(
            select_clause="SELECT resource_id, attributes, resource_type, agent, resource_id_value, environment",
            from_clause=f" FROM {data.Resource.table_name()}",
            filter_statements=["environment = $1", "model = $2"],
            values=[self.environment.id, self.version],
        )
        return query_builder

    def construct_dtos(self, records: Sequence[Record]) -> Sequence[model.VersionedResource]:
        return [
            model.VersionedResource(
                resource_id=versioned_resource["resource_id"],
                resource_version_id=versioned_resource["resource_id"] + f",v={self.version}",
                id_details=data.Resource.get_details_from_resource_id(versioned_resource["resource_id"]),
                requires=json.loads(versioned_resource["attributes"]).get("requires", []),  # todo: broken
            )
            for versioned_resource in records
        ]


class CompileReportView(DataView[CompileReportOrder, CompileReport]):
    def __init__(
        self,
        environment: data.Environment,
        limit: Optional[int] = None,
        filter: Optional[dict[str, list[str]]] = None,
        sort: str = "resource_type.desc",
        first_id: Optional[UUID] = None,
        last_id: Optional[UUID] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            order=CompileReportOrder.parse_from_string(sort),
            limit=limit,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            filter=filter,
        )
        self.environment = environment

    @property
    def allowed_filters(self) -> dict[str, type[Filter]]:
        return {
            "requested": DateRangeFilter,
            "success": BooleanEqualityFilter,
            "started": BooleanIsNotNullFilter,
            "completed": BooleanIsNotNullFilter,
        }

    def get_base_url(self) -> str:
        return "/api/v2/compilereport"

    def get_base_query(self) -> SimpleQueryBuilder:
        query_builder = SimpleQueryBuilder(
            select_clause="""SELECT id, remote_id, environment, requested,
                            started, completed, do_export, force_update,
                            metadata, requested_environment_variables, used_environment_variables,
                            mergeable_environment_variables,
                            success, version, partial, removed_resource_sets, exporter_plugin,
                            notify_failed_compile, failed_compile_message""",
            from_clause=f" FROM {data.Compile.table_name()}",
            filter_statements=["environment = $1"],
            values=[self.environment.id],
        )
        return query_builder

    def construct_dtos(self, records: Sequence[Record]) -> Sequence[model.CompileReport]:
        return [
            CompileReport(
                id=compile["id"],
                remote_id=compile["remote_id"],
                environment=compile["environment"],
                requested=compile["requested"],
                started=compile["started"],
                completed=compile["completed"],
                success=compile["success"],
                version=compile["version"],
                do_export=compile["do_export"],
                force_update=compile["force_update"],
                metadata=json.loads(compile["metadata"]) if compile["metadata"] else {},
                environment_variables=(
                    json.loads(compile["used_environment_variables"]) if compile["used_environment_variables"] else {}
                ),
                requested_environment_variables=json.loads(compile["requested_environment_variables"]),
                mergeable_environment_variables=json.loads(compile["mergeable_environment_variables"]),
                partial=compile["partial"],
                removed_resource_sets=compile["removed_resource_sets"],
                exporter_plugin=compile["exporter_plugin"],
                notify_failed_compile=compile["notify_failed_compile"],
                failed_compile_message=compile["failed_compile_message"],
                links=cast(dict[str, list[str]], compile.get("links", {})),
            )
            for compile in records
        ]


class DesiredStateVersionView(DataView[DesiredStateVersionOrder, DesiredStateVersion]):
    def __init__(
        self,
        environment: data.Environment,
        limit: Optional[int] = None,
        filter: Optional[dict[str, list[str]]] = None,
        sort: str = "resource_type.desc",
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> None:
        super().__init__(
            order=DesiredStateVersionOrder.parse_from_string(sort),
            limit=limit,
            first_id=None,
            last_id=None,
            start=start,
            end=end,
            filter=filter,
        )
        self.environment = environment

    @property
    def allowed_filters(self) -> dict[str, type[Filter]]:
        return {
            "version": IntRangeFilter,
            "date": DateRangeFilter,
            "status": ContainsFilter,
            "released": BooleanEqualityFilter,
        }

    def get_base_url(self) -> str:
        return "/api/v2/desiredstate"

    def get_base_query(self) -> SimpleQueryBuilder:
        scheduled_version = f"""SELECT last_processed_model_version FROM {Scheduler.table_name()} WHERE environment = $1"""
        scheduled_version = f"(SELECT COALESCE(({scheduled_version}), 0))"
        query_builder = SimpleQueryBuilder(
            select_clause=f"""SELECT cm.version, cm.date, cm.total,
                                           version_info -> 'export_metadata' ->> 'message' as message,
                                           version_info -> 'export_metadata' ->> 'type' as type,
                                          (CASE WHEN cm.version = {scheduled_version} THEN 'active'
                                              WHEN cm.version > {scheduled_version} THEN 'candidate'
                                              WHEN cm.version < {scheduled_version} AND cm.released=TRUE THEN 'retired'
                                              ELSE 'skipped_candidate'
                                          END) as status,
                                          cm.released as released""",
            from_clause=f" FROM {ConfigurationModel.table_name()} as cm",
            filter_statements=[" environment =  $1"],
            values=[self.environment.id],
        )
        subquery, subquery_values = query_builder.build()
        query_builder = SimpleQueryBuilder(
            select_clause="SELECT *",
            from_clause=f" FROM ({subquery}) as result",
            values=subquery_values,
        )
        return query_builder

    def construct_dtos(self, records: Sequence[Record]) -> Sequence[DesiredStateVersion]:
        return [
            DesiredStateVersion(
                version=desired_state["version"],
                date=desired_state["date"],
                total=desired_state["total"],
                labels=(
                    [DesiredStateLabel(name=desired_state["type"], message=desired_state["message"])]
                    if desired_state["type"] and desired_state["message"]
                    else []
                ),
                status=desired_state["status"],
                released=cast(bool, desired_state["released"]),
            )
            for desired_state in records
        ]


class ResourceHistoryView(DataView[ResourceHistoryOrder, ResourceHistory]):
    def __init__(
        self,
        environment: data.Environment,
        rid: ResourceIdStr,
        limit: Optional[int] = None,
        sort: str = "resource_type.desc",
        first_id: Optional[str] = None,
        last_id: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            order=ResourceHistoryOrder.parse_from_string(sort),
            limit=limit,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            filter={},
        )
        self.environment = environment
        self.rid = rid

    @property
    def allowed_filters(self) -> dict[str, type[Filter]]:
        return {}

    def get_base_url(self) -> str:
        return f"/api/v2/resource/{urllib.parse.quote(self.rid, safe='')}/history"

    def get_base_query(self) -> SimpleQueryBuilder:
        query_builder = SimpleQueryBuilder(
            prelude="""
            /* Assign a sequence id to the rows, which is used for grouping consecutive ones with the same hash */
                WITH resourcewithsequenceids AS (
                  SELECT
                    attribute_hash,
                    model,
                    attributes,
                    date,
                    ROW_NUMBER() OVER (ORDER BY date) - ROW_NUMBER() OVER (
                      PARTITION BY attribute_hash
                      ORDER BY date
                    ) AS seqid
                  FROM resource JOIN configurationmodel cm
                    ON resource.model = cm.version AND resource.environment = cm.environment
                  WHERE resource.environment = $1 AND resource_id = $2 AND cm.released = TRUE
                )
            """,
            select_clause="SELECT attribute_hash, date, attributes, model",
            from_clause="""
            FROM (SELECT
                    attribute_hash,
                    min(date) as date,
                    min(model) as model,
                        (SELECT distinct on (attribute_hash) attributes
                            FROM resourcewithsequenceids
                            WHERE resourcewithsequenceids.attribute_hash = rs.attribute_hash
                            AND resourcewithsequenceids.seqid = rs.seqid
                            ORDER BY attribute_hash, model
                        ) as attributes
                    FROM resourcewithsequenceids rs
                    GROUP BY attribute_hash,  seqID) as sub
            """,
            values=[self.environment.id, self.rid],
        )
        return query_builder

    def construct_dtos(self, records: Sequence[Record]) -> Sequence[ResourceHistory]:
        def get_attributes(record: Record) -> JsonType:
            attributes = json.loads(record["attributes"])
            if "version" not in attributes:
                # Due to a bug, the version field has always been present in the attributes dictionary.
                # This bug has been fixed in the database. For backwards compatibility reason we here make sure that the
                # version field is present in the attributes dictionary served out via the API.
                attributes["version"] = record["model"]
            return attributes

        return [
            ResourceHistory(
                resource_id=self.rid,
                attribute_hash=record["attribute_hash"],
                attributes=get_attributes(record),
                date=record["date"],
                requires=[Id.parse_id(rid).resource_str() for rid in json.loads(record["attributes"]).get("requires", [])],
            )
            for record in records
        ]


class ResourceLogsView(DataView[ResourceLogOrder, ResourceLog]):
    def __init__(
        self,
        environment: data.Environment,
        rid: ResourceIdStr,
        limit: Optional[int] = None,
        sort: str = "resource_type.desc",
        filter: Optional[dict[str, list[str]]] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            order=ResourceLogOrder.parse_from_string(sort),
            limit=limit,
            first_id=None,
            last_id=None,
            start=start,
            end=end,
            filter=filter,
        )
        self.environment = environment
        self.rid = rid

    @property
    def allowed_filters(self) -> dict[str, type[Filter]]:
        return {
            "minimal_log_level": LogLevelFilter,
            "timestamp": DateRangeFilter,
            "message": ContainsPartialFilter,
            "action": ContainsFilterResourceAction,
        }

    def process_filters(self, filter: Optional[Mapping[str, Sequence[str]]]) -> dict[str, QueryFilter]:
        # Change the api names of the filters to the names used internally in the database
        query = super().process_filters(filter)
        if query.get("minimal_log_level"):
            filter_value = query.pop("minimal_log_level")
            query["level"] = filter_value
        if query.get("message"):
            filter_value = query.pop("message")
            query["msg"] = filter_value
        return query

    def get_base_url(self) -> str:
        return f"/api/v2/resource/{urllib.parse.quote(self.rid, safe='')}/logs"

    def get_base_query(self) -> SimpleQueryBuilder:
        query_builder = SimpleQueryBuilder(
            prelude=f"""
                -- Get all resource action in the given environment for the given resource_id
                WITH actions AS (
                    SELECT  ra.*
                    FROM {Resource.table_name()} AS r INNER JOIN resourceaction_resource AS rr ON (
                                                          r.environment=rr.environment
                                                          AND r.resource_id=rr.resource_id
                                                          AND r.model=rr.resource_version
                                                      )
                                                      INNER JOIN {ResourceAction.table_name()} AS ra ON (
                                                          rr.resource_action_id=ra.action_id
                                                      )
                    WHERE r.environment=$1 AND r.resource_id=$2
                )
            """,
            select_clause="SELECT action_id, action, timestamp, unnested_message",
            from_clause="""
            FROM
                (
                    SELECT action_id,
                           action,
                           (unnested_message ->> 'timestamp')::timestamptz AS timestamp,
                           unnested_message ->> 'level' AS level,
                           unnested_message ->> 'msg' AS msg,
                           unnested_message
                    FROM actions, unnest(messages) AS unnested_message
                ) AS unnested
            """,
            values=[self.environment.id, self.rid],
        )
        return query_builder

    def construct_dtos(self, records: Sequence[Record]) -> Sequence[ResourceLog]:
        logs = []
        for record in records:
            message = json.loads(record["unnested_message"])
            logs.append(
                ResourceLog(
                    action_id=record["action_id"],
                    action=record["action"],
                    timestamp=record["timestamp"],
                    level=message.get("level"),
                    msg=message.get("msg"),
                    args=message.get("args", []),
                    kwargs=message.get("kwargs", {}),
                )
            )
        return logs


class FactsView(DataView[FactOrder, Fact]):
    def __init__(
        self,
        environment: data.Environment,
        limit: Optional[int] = None,
        sort: str = "resource_type.desc",
        first_id: Optional[UUID] = None,
        last_id: Optional[UUID] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        filter: Optional[dict[str, list[str]]] = None,
    ) -> None:
        super().__init__(
            order=FactOrder.parse_from_string(sort),
            limit=limit,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            filter=filter,
        )
        self.environment = environment

    @property
    def allowed_filters(self) -> dict[str, type[Filter]]:
        return {
            "name": ContainsPartialFilter,
            "resource_id": ContainsPartialFilter,
            "expires": BooleanEqualityFilter,
        }

    def get_base_url(self) -> str:
        return "/api/v2/facts"

    def get_base_query(self) -> SimpleQueryBuilder:
        query_builder = SimpleQueryBuilder(
            select_clause="SELECT p.id, p.name, p.value, p.source, p.resource_id, p.updated, p.metadata, p.environment",
            from_clause=f"FROM {Parameter.table_name()} as p",
            filter_statements=["p.environment = $1 ", "p.source = 'fact'"],
            values=[self.environment.id],
        )
        return query_builder

    def construct_dtos(self, records: Sequence[Record]) -> Sequence[Fact]:
        return [
            Fact(
                id=fact["id"],
                name=fact["name"],
                value=fact["value"],
                source=fact["source"],
                updated=fact["updated"],
                resource_id=fact["resource_id"],
                metadata=json.loads(fact["metadata"]) if fact["metadata"] else None,
                environment=fact["environment"],
            )
            for fact in records
        ]


class NotificationsView(DataView[NotificationOrder, model.Notification]):
    def __init__(
        self,
        environment: data.Environment,
        limit: Optional[int] = None,
        sort: str = "resource_type.desc",
        first_id: Optional[UUID] = None,
        last_id: Optional[UUID] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        filter: Optional[dict[str, list[str]]] = None,
    ) -> None:
        super().__init__(
            order=NotificationOrder.parse_from_string(sort),
            limit=limit,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            filter=filter,
        )
        self.environment = environment

    @property
    def allowed_filters(self) -> dict[str, type[Filter]]:
        return {
            "title": ContainsPartialFilter,
            "message": ContainsPartialFilter,
            "read": BooleanEqualityFilter,
            "cleared": BooleanEqualityFilter,
            "severity": ContainsFilter,
        }

    def get_base_url(self) -> str:
        return "/api/v2/notification"

    def get_base_query(self) -> SimpleQueryBuilder:
        return SimpleQueryBuilder(
            select_clause="""SELECT n.*""",
            from_clause=f" FROM {Notification.table_name()} as n",
            filter_statements=[" environment = $1 "],
            values=[self.environment.id],
        )

    def construct_dtos(self, records: Sequence[Record]) -> Sequence[model.Notification]:
        return [
            model.Notification(
                id=notification["id"],
                title=notification["title"],
                message=notification["message"],
                severity=notification["severity"],
                created=notification["created"],
                read=notification["read"],
                cleared=notification["cleared"],
                uri=notification["uri"],
                environment=notification["environment"],
                compile_id=notification["compile_id"],
            )
            for notification in records
        ]


class ParameterView(DataView[ParameterOrder, model.Parameter]):
    def __init__(
        self,
        environment: data.Environment,
        limit: Optional[int] = None,
        sort: str = "resource_type.desc",
        first_id: Optional[UUID] = None,
        last_id: Optional[UUID] = None,
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
        filter: Optional[dict[str, list[str]]] = None,
    ) -> None:
        super().__init__(
            order=ParameterOrder.parse_from_string(sort),
            limit=limit,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            filter=filter,
        )
        self.environment = environment

    @property
    def allowed_filters(self) -> dict[str, type[Filter]]:
        return {
            "name": ContainsPartialFilter,
            "source": ContainsPartialFilter,
            "updated": DateRangeFilter,
        }

    def get_base_url(self) -> str:
        return "/api/v2/parameters"

    def get_base_query(self) -> SimpleQueryBuilder:
        return SimpleQueryBuilder(
            select_clause="""SELECT p.id, p.name, p.value, p.source, p.updated, p.metadata, p.environment""",
            from_clause=f"FROM {Parameter.table_name()} as p",
            filter_statements=["environment = $1", "p.source != 'fact'"],
            values=[self.environment.id],
        )

    def construct_dtos(self, records: Sequence[Record]) -> Sequence[model.Parameter]:
        return [
            model.Parameter(
                id=parameter["id"],
                name=parameter["name"],
                value=parameter["value"],
                source=parameter["source"],
                updated=parameter["updated"],
                metadata=json.loads(parameter["metadata"]) if parameter["metadata"] else None,
                environment=parameter["environment"],
            )
            for parameter in records
        ]


class AgentView(DataView[AgentOrder, model.Agent]):
    def __init__(
        self,
        environment: data.Environment,
        limit: Optional[int] = None,
        sort: str = "resource_type.desc",
        start: Optional[Union[datetime, bool, str]] = None,
        end: Optional[Union[datetime, bool, str]] = None,
        first_id: Optional[str] = None,
        last_id: Optional[str] = None,
        filter: Optional[dict[str, list[str]]] = None,
    ) -> None:
        super().__init__(
            order=AgentOrder.parse_from_string(sort),
            limit=limit,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            filter=filter,
        )
        self.environment = environment

    @property
    def allowed_filters(self) -> dict[str, type[Filter]]:
        return {
            "name": ContainsPartialFilter,
            "process_name": ContainsPartialFilter,
            "status": ContainsFilter,
        }

    def process_filters(self, filter: Optional[Mapping[str, Sequence[str]]]) -> dict[str, QueryFilter]:
        out_filter = super().process_filters(filter)
        # name is ambiguous, qualify
        if "name" in out_filter:
            out_filter["a.name"] = out_filter.pop("name")
        return out_filter

    def get_base_url(self) -> str:
        return "/api/v2/agents"

    def get_base_query(self) -> SimpleQueryBuilder:
        base = SimpleQueryBuilder(
            select_clause=f"""SELECT a.name,
                                     a.environment,
                                     a.last_failover,
                                     a.paused,
                                     a.unpause_on_resume,
                                     NULL AS process_name,
                                     NULL AS process_id,
                                     (
                                         CASE
                                             WHEN a.paused
                                                 THEN 'paused'
                                             WHEN EXISTS(
                                                 SELECT 1
                                                 FROM {data.Agent.table_name()} AS a_inner
                                                 WHERE a_inner.environment=$1
                                                       AND a_inner.name=$2
                                                       AND a_inner.id_primary IS NOT NULL
                                             )
                                                 THEN 'up'
                                                 ELSE 'down'
                                         END
                                     ) AS status
                          """,
            from_clause=f"""
                            FROM {Agent.table_name()} a
                            """,
            filter_statements=[" a.environment = $1 ", " a.name <> $2 "],
            values=[self.environment.id, const.AGENT_SCHEDULER_ID],
        )
        # wrap when using compound fields
        virtual_fields = {"status", "process_name", "process_id"}
        used_fields = set(self.filter.keys()).union({t[0] for t in self.order.get_order_elements(False)})
        if virtual_fields.intersection(used_fields):
            query, values = base.build()
            return SimpleQueryBuilder(
                select_clause="select *",
                from_clause=f"FROM ({query}) as a",
                values=values,
            )
        return base

    def construct_dtos(self, records: Sequence[Record]) -> Sequence[model.Agent]:
        return [
            model.Agent(
                name=agent["name"],
                environment=agent["environment"],
                last_failover=agent["last_failover"],
                paused=agent["paused"],
                unpause_on_resume=agent["unpause_on_resume"],
                process_id=agent["process_id"],
                process_name=agent["process_name"],
                status=agent["status"],
            )
            for agent in records
        ]


class DiscoveredResourceView(DataView[DiscoveredResourceOrder, model.DiscoveredResource]):
    def __init__(
        self,
        environment: data.Environment,
        limit: Optional[int] = None,
        sort: str = "discovered_resource_id.asc",
        start: Optional[str] = None,
        end: Optional[str] = None,
        filter: Optional[Mapping[str, Sequence[str]]] = None,
    ) -> None:
        super().__init__(
            order=DiscoveredResourceOrder.parse_from_string(sort),
            limit=limit,
            first_id=None,
            last_id=None,
            start=start,
            end=end,
            filter=filter,
        )
        self.environment = environment

    @property
    def allowed_filters(self) -> dict[str, type[Filter]]:
        """
        Return the specification of the allowed filters, see FilterValidator
        """
        return {
            "resource_type": ContainsPartialFilter,
            "agent": ContainsPartialFilter,
            "resource_id_value": ContainsPartialFilter,
            "managed": BooleanEqualityFilter,
        }

    def get_base_url(self) -> str:
        return "/api/v2/discovered"

    def get_base_query(self) -> SimpleQueryBuilder:
        query_builder = SimpleQueryBuilder(
            select_clause="SELECT *",
            prelude=f"""
            WITH result AS (
                SELECT
                    dr.environment,
                    dr.discovered_resource_id,
                    dr.resource_type,
                    dr.agent,
                    dr.resource_id_value,
                    dr.values,
                    (rps_1.resource_id IS NOT NULL) AS managed,
                    rps_2.resource_id AS discovery_resource_id

                FROM {data.DiscoveredResource.table_name()} as dr

                -- Retrieve the corresponding managed resource id (if any)
                LEFT JOIN {data.ResourcePersistentState.table_name()} rps_1
                ON dr.environment=rps_1.environment AND dr.discovered_resource_id = rps_1.resource_id

                -- Retrieve the id of the resource responsible for discovering this resource
                LEFT JOIN {data.ResourcePersistentState.table_name()} rps_2
                ON dr.environment=rps_2.environment AND dr.discovery_resource_id = rps_2.resource_id

                WHERE dr.environment = $1
            )
            """,
            from_clause="FROM result AS r",
            values=[self.environment.id],
        )
        return query_builder

    def construct_dtos(self, records: Sequence[Record]) -> Sequence[dict[str, str]]:
        return [
            model.DiscoveredResource(
                discovered_resource_id=rid.resource_str(),
                resource_type=rid.entity_type,
                agent=rid.agent_name,
                resource_id_value=rid.attribute_value,
                values=json.loads(res["values"]),
                managed_resource_uri=(
                    f"/api/v2/resource/{urllib.parse.quote(str(res['discovered_resource_id']), safe='')}"
                    if res["managed"]
                    else None
                ),
                discovery_resource_id=res["discovery_resource_id"] if res["discovery_resource_id"] else None,
            ).model_dump()
            for rid, res in ((Id.parse_id(res["discovered_resource_id"]), res) for res in records)
        ]


class PreludeBasedFilteringQueryBuilder(SimpleQueryBuilder):
    """
    A query builder that applies any filters and the LIMIT statement to the prelude query rather than the outer query.
    The outer query may use the table name "prelude" to refer to the inner query.
    """

    def __init__(
        self,
        prelude_query_builder: SimpleQueryBuilder,
        select_clause: Optional[str] = None,
        from_clause: Optional[str] = None,
        db_order: Optional[DatabaseOrderV2] = None,
        backward_paging: bool = False,
    ) -> None:
        super().__init__(
            select_clause=select_clause,
            from_clause=from_clause,
            filter_statements=None,
            values=None,
            db_order=db_order,
            limit=None,
            backward_paging=backward_paging,
            prelude=None,
        )
        self._prelude_query_builder = prelude_query_builder

    @property
    def offset(self) -> int:
        """The current offset of the values to be used for filter statements"""
        return len(self.values) + len(self._prelude_query_builder.values) + 1

    def build(self) -> tuple[str, list[object]]:
        prelude_query, prelude_values = self._prelude_query_builder.build()
        prelude_query_in_with_block = f"WITH prelude AS ({prelude_query})"
        delegate: SimpleQueryBuilder = SimpleQueryBuilder(
            select_clause=self.select_clause,
            from_clause=self._from_clause,
            filter_statements=self._prelude_query_builder.filter_statements + self.filter_statements,
            values=self._prelude_query_builder.values + self.values,
            db_order=self.db_order,
            limit=None,
            backward_paging=self.backward_paging,
            prelude=prelude_query_in_with_block,
        )
        full_query, values_full = delegate.build()
        return full_query, prelude_values

    def select(self, select_clause: str) -> "PreludeBasedFilteringQueryBuilder":
        """Set the select clause of the query"""
        return PreludeBasedFilteringQueryBuilder(
            select_clause=select_clause,
            from_clause=self._from_clause,
            db_order=self.db_order,
            backward_paging=self.backward_paging,
            prelude_query_builder=self._prelude_query_builder,
        )

    def from_clause(self, from_clause: str) -> "PreludeBasedFilteringQueryBuilder":
        """Set the from clause of the query"""
        return PreludeBasedFilteringQueryBuilder(
            select_clause=self.select_clause,
            from_clause=from_clause,
            db_order=self.db_order,
            backward_paging=self.backward_paging,
            prelude_query_builder=self._prelude_query_builder,
        )

    def order_and_limit(
        self, db_order: DatabaseOrderV2, limit: Optional[int] = None, backward_paging: bool = False
    ) -> "PreludeBasedFilteringQueryBuilder":
        """Set the order and limit of the query"""
        return PreludeBasedFilteringQueryBuilder(
            select_clause=self.select_clause,
            from_clause=self._from_clause,
            db_order=db_order,
            backward_paging=backward_paging,
            prelude_query_builder=self._prelude_query_builder.order_and_limit(db_order, limit, backward_paging),
        )

    def filter(self, filter_statements: list[str], values: list[object]) -> "PreludeBasedFilteringQueryBuilder":
        return PreludeBasedFilteringQueryBuilder(
            select_clause=self.select_clause,
            from_clause=self._from_clause,
            db_order=self.db_order,
            backward_paging=self.backward_paging,
            prelude_query_builder=self._prelude_query_builder.filter(filter_statements, values),
        )
