import abc
import json
from abc import ABC
from typing import Dict, Generic, Iterable, List, Optional, Sequence, Type, TypeVar, Union, cast
from urllib import parse

from asyncpg import Record

from inmanta import data
from inmanta.data import (
    APILIMIT,
    ColumnType,
    DatabaseOrder,
    DatabaseOrderV2,
    InvalidQueryParameter,
    PagingOrder,
    QueryFilter,
    ResourceOrder,
    SimpleQueryBuilder,
    VersionedResourceOrder,
    model,
)
from inmanta.data.model import BaseModel, LatestReleasedResource, PagingBoundaries, ResourceVersionIdStr, VersionedResource
from inmanta.data.paging import PagingMetadata
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.exceptions import BadRequest
from inmanta.protocol.return_value_meta import ReturnValueWithMeta
from inmanta.server.validate_filter import CombinedContainsFilterResourceState, ContainsPartialFilter, Filter, FilterValidator
from inmanta.types import SimpleTypes

T_ORDER = TypeVar("T_ORDER", bound=DatabaseOrderV2)
T_DTO = TypeVar("T_DTO", bound=BaseModel)


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
        self.page_boundaries = PagingBoundaries(start, end, first_id, last_id)  # TODO: types
        self.validate_paging_parameters()

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
    async def get_data(self) -> Sequence[T_DTO]:
        """
        Fetch the data and construct dto's

        See existing implementations for typical usage
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
        backward_paging: bool = (order == PagingOrder.ASC and self.page_boundaries.end is not None) or (
            order == PagingOrder.DESC and self.page_boundaries.start is not None
        )

        return (
            query_builder.filter(
                *self.order.as_filter(
                    query_builder.offset, self.page_boundaries.start, self.page_boundaries.first_id, start=True
                )
            )
            .filter(
                *self.order.as_filter(query_builder.offset, self.page_boundaries.end, self.page_boundaries.last_id, start=False)
            )
            .order_and_limit(self.order, self.limit, backward_paging)
        )

    async def execute(self) -> ReturnValue[Sequence[T_DTO]]:
        dtos = await self.get_data()
        if dtos:
            paging_boundaries = self._get_paging_boundaries_for(dtos)
        else:
            # nothing found now, use the current page to determine if something exists before us
            paging_boundaries = self.page_boundaries
        metadata = await self._get_page_count(paging_boundaries)
        links = await self.prepare_paging_links(dtos, paging_boundaries, metadata)
        return ReturnValueWithMeta(response=dtos, links=links if links else {}, metadata=vars(metadata))

        # Paging helpers

    def _get_paging_boundaries_for(self, dtos: Sequence[T_DTO]) -> PagingBoundaries:
        """Return the page boundaries for the list of dtos"""
        if self.order.get_order() == "DESC":
            first = dtos[0]
            last = dtos[-1]
        else:
            first = dtos[-1]
            last = dtos[0]

        order_column_name = self.order.order_by_column
        order_type: ColumnType = self.order.get_valid_sort_columns()[self.order.order_by_column]

        # TODO get data from records instead of DTO's to have one less domain to mess with?
        return PagingBoundaries(
            start=order_type.get_value(first.all_fields[order_column_name]),  # TODO allfields is not very nice
            first_id=self.order.get_id_from_dto(first),
            end=order_type.get_value(last.all_fields[order_column_name]),
            last_id=self.order.get_id_from_dto(last),
        )

    async def _get_page_count(self, bounds: PagingBoundaries) -> PagingMetadata:
        query_builder = self.get_base_query()

        query_builder = query_builder.filter(
            *data.Resource.get_composed_filter_with_query_types(offset=query_builder.offset, **self.filter)
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
            f"SELECT COUNT(*) as count_total"
            + (f", COUNT(*) filter ({before_filter}) as count_before" if before_filter else "")
            + (f", COUNT(*) filter ({after_filter}) as count_after " if after_filter else "")
        )

        query_builder = query_builder.select(select_clause)

        sql_query, values = query_builder.build()
        result = await data.Resource.select_query(sql_query, values, no_obj=True)
        result = cast(List[Record], result)
        if not result:
            raise InvalidQueryParameter(f"Environment {self.environment} doesn't exist")  # TODO???
        return PagingMetadata(
            total=result[0]["count_total"],
            before=result[0].get("count_before", 0),
            after=result[0].get("count_after", 0),
            page_size=self.limit,
        )

    async def prepare_paging_links(
        self,
        dtos: Sequence[T_DTO],
        paging_boundaries: PagingBoundaries,
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

            def make_link(**args: str) -> str:
                params = url_query_params.copy()
                params.update({k: v for k, v in args.items() if v is not None})
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

    def validate_paging_parameters(
        self,
    ) -> None:
        start = self.page_boundaries.start
        end = self.page_boundaries.end
        first_id = self.page_boundaries.first_id
        last_id = self.page_boundaries.last_id
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
            from_clause=f"FROM cte",
            values=[self.environment.id],
        )
        return query_builder

    async def get_data(self) -> Sequence[model.LatestReleasedResource]:
        query_builder = self.get_base_query()

        # Project
        query_builder = query_builder.select(select_clause="""SELECT *""")
        query_builder = query_builder.filter(
            *data.Resource.get_composed_filter_with_query_types(offset=query_builder.offset, **self.filter)
        )
        query_builder = self.clip_to_page(query_builder)
        sql_query, values = query_builder.build()

        resource_records = await data.Resource.select_query(sql_query, values, no_obj=True)
        resource_records = cast(Iterable[Record], resource_records)

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

    ## Per view config
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

    async def get_data(self) -> Sequence[model.VersionedResource]:
        query_builder = self.get_base_query()

        # Project
        query_builder = query_builder.select(
            select_clause="""SELECT resource_id, attributes, resource_type, agent, resource_id_value, environment"""
        )
        query_builder = query_builder.filter(
            *data.Resource.get_composed_filter_with_query_types(offset=query_builder.offset, **self.filter)
        )
        query_builder = self.clip_to_page(query_builder)
        sql_query, values = query_builder.build()

        versioned_resource_records = await data.Resource.select_query(sql_query, values, no_obj=True)
        versioned_resource_records = cast(Iterable[Record], versioned_resource_records)

        dtos = [
            model.VersionedResource(
                resource_id=versioned_resource["resource_id"],
                resource_version_id=versioned_resource["resource_id"] + f",v={self.version}",
                id_details=data.Resource.get_details_from_resource_id(versioned_resource["resource_id"]),
                requires=json.loads(versioned_resource["attributes"]).get("requires", []),  # todo: broken
            )
            for versioned_resource in versioned_resource_records
        ]
        return dtos
