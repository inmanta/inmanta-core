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
from abc import ABC
from datetime import datetime
from typing import Dict, Generic, List, Optional, Sequence, Tuple, Type, TypeVar, Union, cast
from urllib import parse
from urllib.parse import quote
from uuid import UUID

from asyncpg import Record

from inmanta import data
from inmanta.data import (
    APILIMIT,
    PRIMITIVE_SQL_TYPES,
    Agent,
    AgentOrder,
    CompileReportOrder,
    ConfigurationModel,
    DatabaseOrderV2,
    DesiredStateVersionOrder,
    FactOrder,
    InvalidQueryParameter,
    InvalidSort,
    Notification,
    NotificationOrder,
    PagingOrder,
    Parameter,
    ParameterOrder,
    QueryFilter,
    ResourceAction,
    ResourceHistoryOrder,
    ResourceLogOrder,
    ResourceOrder,
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
    ResourceIdStr,
    ResourceLog,
    ResourceVersionIdStr,
)
from inmanta.protocol.exceptions import BadRequest
from inmanta.protocol.return_value_meta import ReturnValueWithMeta
from inmanta.resources import Id
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
from inmanta.types import SimpleTypes
from inmanta.util import datetime_utc_isoformat

T_ORDER = TypeVar("T_ORDER", bound=DatabaseOrderV2)
T_DTO = TypeVar("T_DTO", bound=BaseModel)


class RequestedPagingBoundaries:
    """Represents the lower and upper bounds that the user requested for the paging boundaries, if any."""

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


class PagingMetadata:
    def __init__(self, total: int, before: int, after: int, page_size: int) -> None:
        self.total = total
        self.before = before
        self.after = after
        self.page_size = page_size

    def to_dict(self) -> Dict[str, int]:
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
        filter: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        self.limit = self.validate_limit(limit)
        self.raw_filter = filter or {}
        self.filter: Dict[str, QueryFilter] = self.process_filters(filter)
        self.order = order
        self.requested_page_boundaries = RequestedPagingBoundaries(start, end, first_id, last_id)
        self.requested_page_boundaries.validate()

    @abc.abstractmethod
    def get_base_url(self) -> str:
        """
        Return the base URL used to construct the paging links

        e.g. "/api/v2/resource"
        """
        pass

    def get_extra_url_parameters(self) -> Dict[str, str]:
        """
        Return additional URL query parameters required to construct the paging links
        """
        return {}

    async def get_data(self) -> Tuple[Sequence[T_DTO], Optional[PagingBoundaries]]:
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

        paging_boundaries = None
        if dtos:
            paging_boundaries = self.order.get_paging_boundaries(dict(records[0]), dict(records[-1]))
        return dtos, paging_boundaries

    @abc.abstractmethod
    def construct_dtos(self, records: Sequence[Record]) -> Sequence[T_DTO]:
        """
        Convert the sequence of records into a sequence of DTO's
        """
        pass

    @abc.abstractmethod
    def get_base_query(self) -> SimpleQueryBuilder:
        """
        Return the base query to get the data.

        Must contain select, from and where clause if specific filtering is required
        """
        pass

    @property
    @abc.abstractmethod
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        """
        Return the specification of the allowed filters, see FilterValidator
        """
        pass

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
            dtos, paging_boundaries_in = await self.get_data()

            paging_boundaries: Union[PagingBoundaries, RequestedPagingBoundaries]
            if paging_boundaries_in:
                paging_boundaries = paging_boundaries_in
            else:
                # nothing found now, use the current page boundaries to determine if something exists before us
                paging_boundaries = self.requested_page_boundaries

            metadata = await self._get_page_count(paging_boundaries)
            links = await self.prepare_paging_links(dtos, paging_boundaries, metadata)
            return ReturnValueWithMeta(response=dtos, links=links if links else {}, metadata=metadata.to_dict())
        except (InvalidFilter, InvalidSort, data.InvalidQueryParameter, data.InvalidFieldNameException) as e:
            raise BadRequest(e.message) from e

    # Paging helpers

    async def _get_page_count(self, bounds: Union[PagingBoundaries, RequestedPagingBoundaries]) -> PagingMetadata:
        """
        Construct the page counts,

        either from the PagingBoundaries if we have a valid page,
        or from the RequestedPagingBoundaries if we got an empty page
        """
        query_builder = self.get_base_query()

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
        result = cast(List[Record], result)
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
        dtos: Sequence[T_DTO],
        paging_boundaries: Union[PagingBoundaries, RequestedPagingBoundaries],
        meta: PagingMetadata,
    ) -> Dict[str, str]:
        """
        Construct the paging links
        """
        links = {}

        url_query_params: Dict[str, Optional[Union[SimpleTypes, List[str]]]] = {
            "limit": self.limit,
            "sort": str(self.order),
        }

        for key, value in self.raw_filter.items():
            if value is not None:
                url_query_params[f"filter.{key}"] = value

        url_query_params.update(self.get_extra_url_parameters())

        if dtos:
            base_url = self.get_base_url()

            def value_to_string(value: Union[str, int, UUID, datetime]) -> str:
                if isinstance(value, datetime):
                    # Accross API boundaries, all naive datetime instances are assumed UTC.
                    # Returns ISO timestamp implicitly in UTC.
                    return datetime_utc_isoformat(value, naive_utc=True)
                return str(value)

            def make_link(**args: Optional[Union[str, int, UUID, datetime]]) -> str:
                params = url_query_params.copy()
                params.update({k: value_to_string(v) for k, v in args.items() if v is not None})
                return f"{base_url}?{parse.urlencode(params, doseq=True)}"

            link_with_end = make_link(
                end=paging_boundaries.end,
                last_id=paging_boundaries.last_id,
            )
            link_with_start = make_link(
                start=paging_boundaries.start,
                first_id=paging_boundaries.first_id,
            )

            has_next = meta.after > 0
            if has_next:
                if self.order.get_order() == "DESC":
                    links["next"] = link_with_end
                else:
                    links["next"] = link_with_start

            has_prev = meta.before > 0
            if has_prev:
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


class ResourceView(DataView[ResourceOrder, model.LatestReleasedResource]):
    def __init__(
        self,
        env: data.Environment,
        limit: Optional[int] = None,
        first_id: Optional[ResourceVersionIdStr] = None,
        last_id: Optional[ResourceVersionIdStr] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        filter: Optional[Dict[str, List[str]]] = None,
        sort: str = "resource_type.desc",
        deploy_summary: bool = False,
    ) -> None:
        super().__init__(
            order=ResourceOrder.parse_from_string(sort),
            limit=limit,
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            filter=filter,
        )
        self.environment = env
        self.deploy_summary = deploy_summary

    @property
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "resource_type": ContainsPartialFilter,
            "agent": ContainsPartialFilter,
            "resource_id_value": ContainsPartialFilter,
            "status": CombinedContainsFilterResourceState,
        }

    def get_base_url(self) -> str:
        return "/api/v2/resource"

    def get_extra_url_parameters(self) -> Dict[str, str]:
        return {"deploy_summary": str(self.deploy_summary)}

    def get_base_query(self) -> SimpleQueryBuilder:
        def subquery_latest_version_for_single_resource(higher_than: Optional[str]) -> str:
            """
            Returns a subquery to select a single row from a resource table:
                - for the first resource id higher than the given boundary
                - the highest (released) version for which a resource with this id exists

            :param higher_than: If given, the subquery selects the first resource id higher than this value (may be a column).
                If not given, the subquery selects the first resource id, period.
            """
            higher_than_condition: str = f"AND r.resource_id > {higher_than}" if higher_than is not None else ""
            return f"""
                SELECT
                    r.resource_id,
                    r.attributes,
                    r.resource_type,
                    r.agent,
                    r.resource_id_value,
                    r.model,
                    r.environment,
                    (
                        CASE WHEN (SELECT r.model < latest_version.version FROM latest_version)
                            THEN 'orphaned' -- use the CTE to check the status
                            ELSE r.status::text
                        END
                    ) as status
                FROM resource r
                JOIN configurationmodel cm ON r.model = cm.version AND r.environment = cm.environment
                WHERE r.environment = $1 AND cm.released = TRUE {higher_than_condition}
                ORDER BY resource_id, model DESC
                LIMIT 1
            """

        query_builder = SimpleQueryBuilder(
            select_clause="SELECT *",
            prelude=f"""
                /* the recursive CTE is the second one, but it has to be specified after 'WITH' if any of them are recursive */
                /* The latest_version CTE finds the maximum released version number in the environment */
                WITH RECURSIVE latest_version AS (
                    SELECT MAX(public.configurationmodel.version) as version
                    FROM public.configurationmodel
                    WHERE public.configurationmodel.released=TRUE AND environment=$1
                ),
                /*
                emulate a loose (or skip) index scan (https://wiki.postgresql.org/wiki/Loose_indexscan):
                1 resource_id at a time, select the latest (released) version it exists in.
                */
                cte AS (
                    /* Initial row for recursion: select relevant version for first resource */
                    ( {subquery_latest_version_for_single_resource(higher_than=None)} )
                    UNION ALL
                    SELECT next_r.*
                    FROM cte curr_r
                    CROSS JOIN LATERAL (
                        /* Recurse: select relevant version for next resource (one higher in the sort order than current) */
                        {subquery_latest_version_for_single_resource(higher_than="curr_r.resource_id")}
                    ) next_r
                )
            """,
            from_clause="FROM cte r",
            values=[self.environment.id],
        )
        return query_builder

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
        ]
        return dtos


class ResourcesInVersionView(DataView[VersionedResourceOrder, model.VersionedResource]):
    def __init__(
        self,
        environment: data.Environment,
        version: int,
        limit: Optional[int] = None,
        filter: Optional[Dict[str, List[str]]] = None,
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
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
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
        filter: Optional[Dict[str, List[str]]] = None,
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
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
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
                            metadata, environment_variables, success, version,
                            partial, removed_resource_sets, exporter_plugin,
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
                environment_variables=json.loads(compile["environment_variables"]) if compile["environment_variables"] else {},
                partial=compile["partial"],
                removed_resource_sets=compile["removed_resource_sets"],
                exporter_plugin=compile["exporter_plugin"],
                notify_failed_compile=compile["notify_failed_compile"],
                failed_compile_message=compile["failed_compile_message"],
            )
            for compile in records
        ]


class DesiredStateVersionView(DataView[DesiredStateVersionOrder, DesiredStateVersion]):
    def __init__(
        self,
        environment: data.Environment,
        limit: Optional[int] = None,
        filter: Optional[Dict[str, List[str]]] = None,
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
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "version": IntRangeFilter,
            "date": DateRangeFilter,
            "status": ContainsFilter,
        }

    def get_base_url(self) -> str:
        return "/api/v2/desiredstate"

    def get_base_query(self) -> SimpleQueryBuilder:
        subquery, subquery_values = ConfigurationModel.desired_state_versions_subquery(self.environment.id)
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
                labels=[DesiredStateLabel(name=desired_state["type"], message=desired_state["message"])]
                if desired_state["type"] and desired_state["message"]
                else [],
                status=desired_state["status"],
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
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {}

    def get_base_url(self) -> str:
        return f"/api/v2/resource/{quote(self.rid,safe='')}/history"

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
            select_clause="SELECT attribute_hash, date, attributes",
            from_clause="""
            FROM (SELECT
                    attribute_hash,
                    min(date) as date,
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
        return [
            ResourceHistory(
                resource_id=self.rid,
                attribute_hash=record["attribute_hash"],
                attributes=json.loads(record["attributes"]),
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
        filter: Optional[Dict[str, List[str]]] = None,
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
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "minimal_log_level": LogLevelFilter,
            "timestamp": DateRangeFilter,
            "message": ContainsPartialFilter,
            "action": ContainsFilterResourceAction,
        }

    def process_filters(self, filter: Optional[Dict[str, List[str]]]) -> Dict[str, QueryFilter]:
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
        return f"/api/v2/resource/{parse.quote(self.rid, safe='')}/logs"

    def get_base_query(self) -> SimpleQueryBuilder:
        # The query uses a like query to match resource id with a resource_version_id. This means we need to escape the % and _
        # characters in the query
        resource_id = self.rid.replace("#", "##").replace("%", "#%").replace("_", "#_") + "%"
        query_builder = SimpleQueryBuilder(
            select_clause="SELECT action_id, action, timestamp, unnested_message",
            from_clause=f"""
            FROM
                    (SELECT action_id, action, (unnested_message ->> 'timestamp')::timestamptz as timestamp,
                    unnested_message ->> 'level' as level,
                    unnested_message ->> 'msg' as msg,
                    unnested_message
                    FROM {ResourceAction.table_name()}, unnest(resource_version_ids) rvid, unnest(messages) unnested_message
                    WHERE environment = $1 AND rvid LIKE $2 ESCAPE '#') unnested
            """,
            values=[self.environment.id, resource_id],
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
        filter: Optional[Dict[str, List[str]]] = None,
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
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "name": ContainsPartialFilter,
            "resource_id": ContainsPartialFilter,
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
        filter: Optional[Dict[str, List[str]]] = None,
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
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
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
        filter: Optional[Dict[str, List[str]]] = None,
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
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
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
        filter: Optional[Dict[str, List[str]]] = None,
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
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "name": ContainsPartialFilter,
            "process_name": ContainsPartialFilter,
            "status": ContainsFilter,
        }

    def process_filters(self, filter: Optional[Dict[str, List[str]]]) -> Dict[str, QueryFilter]:
        out_filter = super().process_filters(filter)
        # name is ambiguous, qualify
        if "name" in out_filter:
            out_filter["a.name"] = out_filter.pop("name")
        return out_filter

    def get_base_url(self) -> str:
        return "/api/v2/agents"

    def get_base_query(self) -> SimpleQueryBuilder:
        base = SimpleQueryBuilder(
            select_clause="""SELECT a.name, a.environment, last_failover, paused, unpause_on_resume,
                                            ap.hostname as process_name, ai.process as process_id,
                                            (CASE WHEN paused THEN 'paused'
                                                WHEN id_primary IS NOT NULL THEN 'up'
                                                ELSE 'down'
                                            END) as status""",
            from_clause=f" FROM {Agent.table_name()} as a LEFT JOIN public.agentinstance ai ON a.id_primary=ai.id "
            " LEFT JOIN public.agentprocess ap ON ai.process = ap.sid",
            filter_statements=[" a.environment = $1 "],
            values=[self.environment.id],
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
