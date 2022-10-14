import json
from typing import Dict, Iterable, List, Optional, Union, cast
from urllib import parse

from asyncpg import Record

from inmanta import const, data, util
from inmanta.data import (
    APILIMIT,
    ArgumentCollector,
    ColumnType,
    InvalidQueryParameter,
    PagingCounts,
    PagingOrder,
    QueryFilter,
    SimpleQueryBuilder,
    VersionedResourceOrder,
    model,
)
from inmanta.data.model import PagingBoundaries, ResourceVersionIdStr
from inmanta.data.paging import PagingMetadata
from inmanta.protocol.exceptions import BadRequest
from inmanta.server.validate_filter import VersionedResourceFilterValidator
from inmanta.types import SimpleTypes


class ResourcesInVersionView(VersionedResourceFilterValidator):
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
        self.limit = self.validate_limit(limit)
        self.raw_filter = filter
        self.filter: Dict[str, QueryFilter] = self.process_filters(filter)
        self.order: VersionedResourceOrder = VersionedResourceOrder.parse_from_string(sort)
        self.environment = environment
        self.version = version
        self.page_boundaries = PagingBoundaries(start, end, first_id, last_id)  # TODO: types

    def validate_limit(self, limit: Optional[int]) -> int:
        if limit is None:
            return APILIMIT
        if limit > APILIMIT:
            raise BadRequest(f"limit parameter can not exceed {APILIMIT}, got {limit}.")
        return limit

    async def get_data(self) -> List[model.VersionedResource]:
        query_builder = self.get_base_query()

        # Project
        query_builder = query_builder.select(
            select_clause="""SELECT resource_id, attributes, resource_type,
                                            agent, resource_id_value, environment"""
        )

        query_builder = query_builder.filter(
            *data.Resource.get_composed_filter_with_query_types(offset=query_builder.offset, **self.filter)
        )

        query_builder = self.clip_to_page(query_builder)
        query_builder = self.order_and_limit(query_builder)
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

    def get_base_query(self):
        query_builder = SimpleQueryBuilder(
            from_clause=f" FROM {data.Resource.table_name()}",
            filter_statements=["environment = $1", "model = $2"],
            values=[self.environment.id, self.version],
        )
        return query_builder

    def clip_to_page(self, query_builder: SimpleQueryBuilder) -> SimpleQueryBuilder:
        return query_builder.filter(
            *self.order.as_start_filter(query_builder.offset, self.page_boundaries.start, self.page_boundaries.first_id)
        ).filter(*self.order.as_end_filter(query_builder.offset, self.page_boundaries.end, self.page_boundaries.last_id))

    def order_and_limit(self, query_builder: SimpleQueryBuilder) -> SimpleQueryBuilder:
        order = self.order.get_order()
        backward_paging: bool = (order == PagingOrder.ASC and self.page_boundaries.end is not None) or (
            order == PagingOrder.DESC and self.page_boundaries.start is not None
        )
        return query_builder.order_and_limit(self.order, self.limit, backward_paging)

    def _get_paging_boundaries(self, dtos: List[model.VersionedResource]) -> PagingBoundaries:
        if self.order.get_order() == "DESC":
            first = dtos[0]
            last = dtos[-1]
        else:
            first = dtos[-1]
            last = dtos[0]

        order_column_name = self.order.order_by_column
        order_type: ColumnType = self.order.get_valid_sort_columns_new()[self.order.order_by_column]

        return PagingBoundaries(
            start=order_type.get_value(first.all_fields[order_column_name]),  # TODO allfields is not very nice
            first_id=first.resource_id,
            end=order_type.get_value(last.all_fields[order_column_name]),
            last_id=last.resource_id,
        )

    async def _get_page_count(self, bounds: PagingBoundaries) -> PagingMetadata:
        query_builder = self.get_base_query()

        query_builder = query_builder.filter(
            *data.Resource.get_composed_filter_with_query_types(offset=query_builder.offset, **self.filter)
        )

        order = self.order.get_order()
        reversed = order == PagingOrder.DESC  # TODO remove if this works and remove in _get_paging_boundaries

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
            f"SELECT COUNT(*) as count_total, "
            f"COUNT(*) filter ({before_filter}) as count_before, "
            f"COUNT(*) filter ({after_filter}) as count_after "
        )

        query_builder = query_builder.select(select_clause)

        sql_query, values = query_builder.build()
        result = await data.Resource.select_query(sql_query, values, no_obj=True)
        result = cast(List[Record], result)
        if not result:
            raise InvalidQueryParameter(f"Environment {self.environment} doesn't exist")  # TODO???
        return PagingMetadata(
            total=result[0]["count_total"],
            before=result[0]["count_before"],
            after=result[0]["count_after"],
            page_size=self.limit,
        )

    def get_base_url(self) -> str:
        return f"/api/v2/desiredstate/{self.version}"

    async def prepare_paging_links(
        self,
        dtos: List[model.VersionedResource],
        paging_boundaries: PagingBoundaries,
        meta: PagingMetadata,
    ) -> Dict[str, str]:
        links = {}

        url_query_params: Dict[str, Optional[Union[SimpleTypes, List[str]]]] = {
            "limit": self.limit,
            "sort": str(self.order),
        }

        if self.raw_filter:
            for key, value in self.raw_filter.items():
                if value is not None:
                    url_query_params[f"filter.{key}"] = value

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
