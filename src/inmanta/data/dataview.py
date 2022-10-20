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
from uuid import UUID

from asyncpg import Record

from inmanta import data
from inmanta.data import (
    APILIMIT,
    DatabaseOrderV2,
    InvalidQueryParameter,
    PagingOrder,
    QueryFilter,
    ResourceOrder,
    SimpleQueryBuilder,
    VersionedResourceOrder,
    model,
)
from inmanta.data.model import BaseModel, LatestReleasedResource, PagingBoundaries, ResourceVersionIdStr
from inmanta.data.paging import PagingMetadata
from inmanta.protocol.exceptions import BadRequest
from inmanta.protocol.return_value_meta import ReturnValueWithMeta
from inmanta.server.validate_filter import CombinedContainsFilterResourceState, ContainsPartialFilter, Filter, FilterValidator
from inmanta.types import SimpleTypes
from inmanta.util import datetime_utc_isoformat

T_ORDER = TypeVar("T_ORDER", bound=DatabaseOrderV2)
T_DTO = TypeVar("T_DTO", bound=BaseModel)


class RequestedPagingBoundaries:
    """Represents the lower and upper bounds that the user requested for the paging boundaries"""

    def __init__(
        self,
        start: Optional[str],
        end: Optional[str],
        first_id: Optional[str],
        last_id: Optional[str],
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
        if start and end:
            raise InvalidQueryParameter(
                f"Only one of start and end parameters is allowed at the same time. Received start: {start}, end: {end}"
            )
        if first_id and last_id:
            raise InvalidQueryParameter(
                f"Only one of first_id and last_id parameters is allowed at the same time. "
                f"Received first_id: {first_id}, last_id: {last_id}"
            )
        if (first_id and not start) or (first_id and end):
            raise InvalidQueryParameter(
                f"The first_id parameter should be used in combination with the start parameter. "
                f"Received first_id: {first_id}, start: {start}, end: {end}"
            )
        if (last_id and not end) or (last_id and start):
            raise InvalidQueryParameter(
                f"The last_id parameter should be used in combination with the end parameter. "
                f"Received last_id: {last_id}, start: {start}, end: {end}"
            )


class DataView(FilterValidator, Generic[T_ORDER, T_DTO], ABC):
    def __init__(
        self,
        order: T_ORDER,
        limit: Optional[int] = None,
        first_id: Optional[ResourceVersionIdStr] = None,
        last_id: Optional[ResourceVersionIdStr] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
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

    @abc.abstractmethod
    async def get_data(self) -> Tuple[Sequence[T_DTO], Optional[PagingBoundaries]]:
        """
        Fetch the data and construct dto's

        See existing implementations for typical usage

        """
        pass

    @abc.abstractmethod
    def get_base_query(self) -> SimpleQueryBuilder:
        """
        Return the base query to get the data.

        Must contain form clause and where clause if specific filtering is required
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
        backward_paging: bool = (order == PagingOrder.ASC and self.requested_page_boundaries.end is not None) or (
            order == PagingOrder.DESC and self.requested_page_boundaries.start is not None
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

        dtos, paging_boundaries_in = await self.get_data()

        paging_boundaries: Union[PagingBoundaries, RequestedPagingBoundaries]
        if paging_boundaries_in:
            paging_boundaries = paging_boundaries_in
        else:
            # nothing found now, use the current page to determine if something exists before us
            paging_boundaries = self.requested_page_boundaries

        metadata = await self._get_page_count(paging_boundaries)
        links = await self.prepare_paging_links(dtos, paging_boundaries, metadata)
        return ReturnValueWithMeta(response=dtos, links=links if links else {}, metadata=vars(metadata))

        # Paging helpers

    async def _get_page_count(self, bounds: Union[PagingBoundaries, RequestedPagingBoundaries]) -> PagingMetadata:
        """
        Construct the page counts,

        either from the PagingBoundaries if we have a valid page,
        or from the RequestedPagingBoundaries if we got an empty page
        """
        query_builder = self.get_base_query()

        query_builder = query_builder.filter(
            *data.Resource.get_composed_filter_with_query_types(
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
        before_filter_statements, before_values = self.order.as_filter(len(values) + 1, end, last_id, start=reversed)
        values.extend(before_values)

        before_filter = data.BaseDocument._join_filter_statements(before_filter_statements)
        after_filter = data.BaseDocument._join_filter_statements(after_filter_statements)

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
                first_id=paging_boundaries.first_id,
                last_id=paging_boundaries.last_id,
                first=paging_boundaries.start,
                last=paging_boundaries.end,
            )
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
        query_builder = SimpleQueryBuilder(
            prelude="""
            /* the recursive CTE is the second one, but it has to be specified after 'WITH' if any of them are recursive */
            /* The cm_version CTE finds the maximum released version number in the environment  */
            WITH RECURSIVE cm_version AS (
                  SELECT
                    MAX(public.configurationmodel.version) as max_version
                    FROM public.configurationmodel
                WHERE public.configurationmodel.released=TRUE
                AND environment=$1
                ),
            /* emulate a loose (or skip) index scan */
            cte AS (
               (
               /* specify the necessary columns */
               SELECT r.resource_id, r.resource_version_id, r.attributes, r.resource_type,
                    r.agent, r.resource_id_value, r.model, r.environment, (CASE WHEN
                            (SELECT r.model < cm_version.max_version
                            FROM cm_version)
                        THEN 'orphaned' -- use the CTE to check the status
                    ELSE r.status::text END) as status
               FROM   resource r
               JOIN configurationmodel cm ON r.model = cm.version AND r.environment = cm.environment
               WHERE  r.environment = $1 AND cm.released = TRUE
               ORDER  BY resource_id, model DESC
               LIMIT  1
               )
               UNION ALL
               SELECT r.*
               FROM   cte c
               CROSS JOIN LATERAL
               /* specify the same columns in the recursive part */
                (SELECT r.resource_id,  r.resource_version_id, r.attributes, r.resource_type,
                    r.agent, r.resource_id_value, r.model, r.environment, (CASE WHEN
                            (SELECT r.model < cm_version.max_version
                            FROM cm_version)
                        THEN 'orphaned'
                    ELSE r.status::text END) as status
               FROM   resource r JOIN configurationmodel cm on r.model = cm.version AND r.environment = cm.environment
               /* One result from the recursive call is the latest released version of one specific resource.
                  We always start looking for this based on the previous resource_id. */
               WHERE  r.resource_id > c.resource_id AND r.environment = $1 AND cm.released = TRUE
               ORDER  BY r.resource_id, r.model DESC
               LIMIT  1) r
               )
            """,
            from_clause="FROM cte",
            values=[self.environment.id],
        )
        return query_builder

    async def get_data(self) -> Tuple[Sequence[model.LatestReleasedResource], Optional[PagingBoundaries]]:
        query_builder = self.get_base_query()

        # Project
        query_builder = query_builder.select(select_clause="""SELECT *""")
        query_builder = query_builder.filter(
            *data.Resource.get_composed_filter_with_query_types(
                offset=query_builder.offset, col_name_prefix=None, **self.filter
            )
        )
        query_builder = self.clip_to_page(query_builder)
        sql_query, values = query_builder.build()

        resource_records = await data.Resource.select_query(sql_query, values, no_obj=True)

        dtos: Sequence[LatestReleasedResource] = [
            model.LatestReleasedResource(
                resource_id=resource["resource_id"],
                resource_version_id=resource["resource_id"] + ",v=" + str(resource["model"]),
                id_details=data.Resource.get_details_from_resource_id(resource["resource_id"]),
                status=resource["status"],
                requires=json.loads(resource["attributes"]).get("requires", []),
            )
            for resource in resource_records
        ]

        paging_boundaries = None
        if dtos:
            paging_boundaries = self.order.get_paging_boundaries(dict(resource_records[0]), dict(resource_records[-1]))
        return dtos, paging_boundaries


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
            from_clause=f" FROM {data.Resource.table_name()}",
            filter_statements=["environment = $1", "model = $2"],
            values=[self.environment.id, self.version],
        )
        return query_builder

    async def get_data(self) -> Tuple[Sequence[model.VersionedResource], Optional[PagingBoundaries]]:
        query_builder = self.get_base_query()

        # Project
        query_builder = query_builder.select(
            select_clause="""SELECT resource_id, attributes, resource_type, agent, resource_id_value, environment"""
        )
        query_builder = query_builder.filter(
            *data.Resource.get_composed_filter_with_query_types(
                offset=query_builder.offset, col_name_prefix=None, **self.filter
            )
        )
        query_builder = self.clip_to_page(query_builder)
        sql_query, values = query_builder.build()

        versioned_resource_records = await data.Resource.select_query(sql_query, values, no_obj=True)

        dtos = [
            model.VersionedResource(
                resource_id=versioned_resource["resource_id"],
                resource_version_id=versioned_resource["resource_id"] + f",v={self.version}",
                id_details=data.Resource.get_details_from_resource_id(versioned_resource["resource_id"]),
                requires=json.loads(versioned_resource["attributes"]).get("requires", []),  # todo: broken
            )
            for versioned_resource in versioned_resource_records
        ]

        paging_boundaries = None
        if dtos:
            paging_boundaries = self.order.get_paging_boundaries(
                dict(versioned_resource_records[0]), dict(versioned_resource_records[-1])
            )
        return dtos, paging_boundaries
