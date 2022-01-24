"""
    Copyright 2021 Inmanta

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
import datetime
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Mapping, Optional, Tuple, Type, TypeVar, Union
from urllib import parse

from inmanta.data import (
    Agent,
    ColumnNameStr,
    Compile,
    ConfigurationModel,
    DatabaseOrder,
    InvalidFieldNameException,
    InvalidQueryParameter,
    PagingCounts,
    PagingOrder,
    QueryType,
    Resource,
    ResourceAction,
)
from inmanta.data.model import Agent as AgentModel
from inmanta.data.model import (
    BaseModel,
    CompileReport,
    DesiredStateVersion,
    LatestReleasedResource,
    PagingBoundaries,
    ResourceHistory,
    ResourceIdStr,
    VersionedResource,
)
from inmanta.protocol import exceptions
from inmanta.types import SimpleTypes

T = TypeVar("T", bound=BaseModel, covariant=True)


class PagingMetadata:
    def __init__(self, total: int, before: int, after: int, page_size: int) -> None:
        self.total = total
        self.before = before
        self.after = after
        self.page_size = page_size


class QueryIdentifier(BaseModel):
    """ The identifier for a paged query"""

    environment: uuid.UUID


class ResourceQueryIdentifier(QueryIdentifier):
    resource_id: ResourceIdStr


class VersionedQueryIdentifier(QueryIdentifier):
    version: int


class PagingCountsProvider(ABC):
    @abstractmethod
    async def count_items_for_paging(
        self,
        query_identifier: QueryIdentifier,
        database_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        **query: Tuple[QueryType, object],
    ) -> PagingCounts:
        """
        Count the records in the ranges required for the paging links
        """
        pass


class ResourcePagingCountsProvider(PagingCountsProvider):
    def __init__(self, data_class: Type[Resource]) -> None:
        self.data_class = data_class

    async def count_items_for_paging(
        self,
        query_identifier: QueryIdentifier,
        database_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        **query: Tuple[QueryType, object],
    ) -> PagingCounts:
        sql_query, values = self.data_class._get_paging_item_count_query(
            query_identifier.environment,
            database_order,
            ColumnNameStr("resource_version_id"),
            first_id,
            last_id,
            start,
            end,
            **query,
        )
        result = await self.data_class.select_query(sql_query, values, no_obj=True)
        return PagingCounts(total=result[0]["count_total"], before=result[0]["count_before"], after=result[0]["count_after"])


class ResourceHistoryPagingCountsProvider(PagingCountsProvider):
    def __init__(self, data_class: Type[Resource]) -> None:
        self.data_class = data_class

    async def count_items_for_paging(
        self,
        query_identifier: ResourceQueryIdentifier,
        database_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        **query: Tuple[QueryType, object],
    ) -> PagingCounts:
        sql_query, values = self.data_class._get_paging_history_item_count_query(
            query_identifier.environment,
            query_identifier.resource_id,
            database_order,
            ColumnNameStr("attribute_hash"),
            first_id,
            last_id,
            start,
            end,
            **query,
        )
        result = await self.data_class.select_query(sql_query, values, no_obj=True)
        return PagingCounts(total=result[0]["count_total"], before=result[0]["count_before"], after=result[0]["count_after"])


class ResourceLogPagingCountsProvider(PagingCountsProvider):
    def __init__(self, data_class: Type[ResourceAction]) -> None:
        self.data_class = data_class

    async def count_items_for_paging(
        self,
        query_identifier: ResourceQueryIdentifier,
        database_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        **query: Tuple[QueryType, object],
    ) -> PagingCounts:
        sql_query, values = self.data_class._get_paging_resource_log_item_count_query(
            query_identifier.environment,
            query_identifier.resource_id,
            database_order,
            ColumnNameStr("timestamp"),
            first_id,
            last_id,
            start,
            end,
            **query,
        )
        result = await self.data_class.select_query(sql_query, values, no_obj=True)
        return PagingCounts(total=result[0]["count_total"], before=result[0]["count_before"], after=result[0]["count_after"])


class VersionedResourcePagingCountsProvider(PagingCountsProvider):
    async def count_items_for_paging(
        self,
        query_identifier: VersionedQueryIdentifier,
        database_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        **query: Tuple[QueryType, object],
    ) -> PagingCounts:
        return await Resource.count_versioned_resources_for_paging(
            query_identifier.environment,
            query_identifier.version,
            database_order,
            first_id,
            last_id,
            start,
            end,
            **query,
        )


class CompileReportPagingCountsProvider(PagingCountsProvider):
    async def count_items_for_paging(
        self,
        query_identifier: QueryIdentifier,
        database_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        **query: Tuple[QueryType, object],
    ) -> PagingCounts:
        return await Compile.count_items_for_paging(
            query_identifier.environment, database_order, first_id, last_id, start, end, **query
        )


class AgentPagingCountsProvider(PagingCountsProvider):
    async def count_items_for_paging(
        self,
        query_identifier: QueryIdentifier,
        database_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        **query: Tuple[QueryType, object],
    ) -> PagingCounts:
        return await Agent.count_items_for_paging(
            query_identifier.environment, database_order, first_id, last_id, start, end, **query
        )


class DesiredStateVersionPagingCountsProvider(PagingCountsProvider):
    async def count_items_for_paging(
        self,
        query_identifier: QueryIdentifier,
        database_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        **query: Tuple[QueryType, object],
    ) -> PagingCounts:
        return await ConfigurationModel.count_items_for_paging(
            query_identifier.environment, database_order, first_id, last_id, start, end, **query
        )


class PagingHandler(ABC, Generic[T]):
    def __init__(self, counts_provider: PagingCountsProvider) -> None:
        self.counts_provider = counts_provider

    async def prepare_paging_metadata(
        self,
        query_identifier: QueryIdentifier,
        dtos: List[T],
        db_query: Mapping[str, Tuple[QueryType, object]],
        limit: int,
        database_order: DatabaseOrder,
    ) -> PagingMetadata:
        items_on_next_pages = 0
        items_on_prev_pages = 0
        total = 0
        if dtos:
            paging_borders = self._get_paging_boundaries(dtos, database_order)
            start = paging_borders.start
            first_id = paging_borders.first_id
            end = paging_borders.end
            last_id = paging_borders.last_id
            try:
                paging_counts = await self.counts_provider.count_items_for_paging(
                    query_identifier=query_identifier,
                    database_order=database_order,
                    start=start,
                    first_id=first_id,
                    end=end,
                    last_id=last_id,
                    **db_query,
                )
            except (InvalidFieldNameException, InvalidQueryParameter) as e:
                raise exceptions.BadRequest(f"Invalid query specified: {e.message}")
            total = paging_counts.total
            items_on_prev_pages = paging_counts.before
            items_on_next_pages = paging_counts.after
        metadata = PagingMetadata(
            total=total,
            before=items_on_prev_pages,
            after=items_on_next_pages,
            page_size=limit,
        )
        return metadata

    def _get_paging_boundaries(self, dtos: List[T], sort_order: DatabaseOrder) -> PagingBoundaries:
        if sort_order.get_order() == PagingOrder.DESC:
            start_dto = dtos[0].dict()
            end_dto = dtos[-1].dict()
        else:
            start_dto = dtos[-1].dict()
            end_dto = dtos[0].dict()
        return PagingBoundaries(
            start=sort_order.ensure_boundary_type(start_dto[sort_order.get_order_by_column_api_name()]),
            first_id=start_dto[sort_order.id_column],
            end=sort_order.ensure_boundary_type(end_dto[sort_order.get_order_by_column_api_name()]),
            last_id=end_dto[sort_order.id_column],
        )

    def _encode_filter_dict(self, filter: Optional[Dict[str, List[str]]]) -> Dict[str, List[str]]:
        url_query_params = {}
        if filter:
            for key in filter.keys():
                url_query_params[f"filter.{key}"] = filter[key]
        return url_query_params

    @abstractmethod
    def get_base_url(self) -> str:
        """ The base url for the method, with the path parameters already specified (if applicable)"""
        pass

    def get_first_id_name(self) -> str:
        """ The name of the first id parameter in the api, used when creating links """
        return "first_id"

    def get_last_id_name(self) -> str:
        """ The name of the last id parameter in the api, used when creating links """
        return "last_id"

    async def prepare_paging_links(
        self,
        dtos: List[T],
        filter: Optional[Dict[str, List[str]]],
        database_order: DatabaseOrder,
        limit: Optional[int] = None,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[Union[datetime.datetime, int, bool, str]] = None,
        end: Optional[Union[datetime.datetime, int, bool, str]] = None,
        has_next: Optional[bool] = False,
        has_prev: Optional[bool] = False,
        **additional_url_params: Optional[Union[SimpleTypes, List[str]]],
    ) -> Dict[str, str]:
        links = {}

        url_query_params: Dict[str, Optional[Union[SimpleTypes, List[str]]]] = {
            "limit": limit,
            "sort": str(database_order),
            **additional_url_params,
            **self._encode_filter_dict(filter),
        }

        url_query_params_without_paging_position = self._param_dict_without_none_values(url_query_params)

        if limit and dtos:
            base_url = self.get_base_url()
            paging_boundaries = self._get_paging_boundaries(dtos, database_order)
            link_with_end = await self.prepare_link_with_end(
                base_url,
                url_query_params_without_paging_position,
                end=paging_boundaries.end,
                last_id=paging_boundaries.last_id,
            )
            link_with_start = await self.prepare_link_with_start(
                base_url,
                url_query_params_without_paging_position,
                start=paging_boundaries.start,
                first_id=paging_boundaries.first_id,
            )
            if has_next:
                if database_order.get_order() == "DESC":
                    links["next"] = link_with_end
                    # Last page
                    last_page_params = url_query_params_without_paging_position.copy()
                    last_page_start = database_order.get_min_time()
                    # Don't add last page link if we don't have a minimum and the order is descending
                    if last_page_start:
                        last_page_params["start"] = last_page_start
                        links["last"] = self._encode_paging_url(base_url, last_page_params)
                else:
                    links["next"] = link_with_start
                    last_page_params = url_query_params_without_paging_position.copy()
                    last_page_end = database_order.get_max_time()
                    # Don't add last page link if we don't have a maximum and the order is ascending
                    if last_page_end:
                        last_page_params["end"] = last_page_end
                        links["last"] = self._encode_paging_url(base_url, last_page_params)

            if has_prev:
                if database_order.get_order() == "DESC":
                    links["prev"] = link_with_start
                else:
                    links["prev"] = link_with_end
                # First page
                first_page_params = url_query_params_without_paging_position.copy()
                links["first"] = self._encode_paging_url(base_url, first_page_params)

            # Same page
            original_url_query_params = url_query_params_without_paging_position.copy()
            original_url_query_params.update(
                {self.get_first_id_name(): first_id, self.get_last_id_name(): last_id, "start": start, "end": end}
            )
            original_url_query_params = self._param_dict_without_none_values(original_url_query_params)
            links["self"] = self._encode_paging_url(base_url, original_url_query_params)
        return links

    def _param_dict_without_none_values(self, param_dict: Dict[str, Any]) -> Dict[str, Any]:
        return {param_key: param_value for param_key, param_value in param_dict.items() if param_value is not None}

    async def prepare_link_with_start(
        self,
        base_url: str,
        url_query_params_without_paging_params: Dict[str, SimpleTypes],
        first_id: Optional[Union[uuid.UUID, str]],
        start: Union[datetime.datetime, int, str],
    ) -> str:
        previous_params = url_query_params_without_paging_params.copy()
        previous_params["start"] = start
        if first_id:
            previous_params[self.get_first_id_name()] = first_id
        return self._encode_paging_url(base_url, previous_params)

    async def prepare_link_with_end(
        self,
        base_url: str,
        url_query_params_without_paging_params: Dict[str, SimpleTypes],
        last_id: Optional[Union[uuid.UUID, str]],
        end: Union[datetime.datetime, int, str],
    ) -> str:
        next_params = url_query_params_without_paging_params.copy()
        next_params["end"] = end
        if last_id:
            next_params[self.get_last_id_name()] = last_id
        return self._encode_paging_url(base_url, next_params)

    def _encode_paging_url(self, base_url: str, params: Mapping[str, Union[SimpleTypes, List[str]]]) -> str:
        return f"{base_url}?{parse.urlencode(params, doseq=True)}"


class ResourcePagingHandler(PagingHandler[LatestReleasedResource]):
    def __init__(
        self,
        counts_provider: PagingCountsProvider,
    ) -> None:
        super().__init__(counts_provider)

    def get_base_url(self) -> str:
        return "/api/v2/resource"

    def _get_paging_boundaries(self, dtos: List[LatestReleasedResource], sort_order: DatabaseOrder) -> PagingBoundaries:
        if sort_order.get_order() == "DESC":
            return PagingBoundaries(
                start=sort_order.ensure_boundary_type(dtos[0].all_fields[sort_order.get_order_by_column_api_name()]),
                first_id=dtos[0].resource_version_id,
                end=sort_order.ensure_boundary_type(dtos[-1].all_fields[sort_order.get_order_by_column_api_name()]),
                last_id=dtos[-1].resource_version_id,
            )
        else:
            return PagingBoundaries(
                start=sort_order.ensure_boundary_type(dtos[-1].all_fields[sort_order.get_order_by_column_api_name()]),
                first_id=dtos[-1].resource_version_id,
                end=sort_order.ensure_boundary_type(dtos[0].all_fields[sort_order.get_order_by_column_api_name()]),
                last_id=dtos[0].resource_version_id,
            )


class ResourceHistoryPagingHandler(PagingHandler[ResourceHistory]):
    def __init__(
        self,
        counts_provider: PagingCountsProvider,
        resource_id: str,
    ) -> None:
        super().__init__(counts_provider)
        self.resource_id = resource_id

    def get_base_url(self) -> str:
        return f"/api/v2/resource/{parse.quote(self.resource_id, safe='')}/history"

    def _get_paging_boundaries(self, dtos: List[ResourceHistory], sort_order: DatabaseOrder) -> PagingBoundaries:
        if sort_order.get_order() == "DESC":
            return PagingBoundaries(
                start=sort_order.ensure_boundary_type(dtos[0].dict()[sort_order.get_order_by_column_api_name()]),
                first_id=dtos[0].attribute_hash,
                end=sort_order.ensure_boundary_type(dtos[-1].dict()[sort_order.get_order_by_column_api_name()]),
                last_id=dtos[-1].attribute_hash,
            )
        else:
            return PagingBoundaries(
                start=sort_order.ensure_boundary_type(dtos[-1].dict()[sort_order.get_order_by_column_api_name()]),
                first_id=dtos[-1].attribute_hash,
                end=sort_order.ensure_boundary_type(dtos[0].dict()[sort_order.get_order_by_column_api_name()]),
                last_id=dtos[0].attribute_hash,
            )


class ResourceLogPagingHandler(PagingHandler[ResourceHistory]):
    def __init__(
        self,
        counts_provider: PagingCountsProvider,
        resource_id: str,
    ) -> None:
        super().__init__(counts_provider)
        self.resource_id = resource_id

    def get_base_url(self) -> str:
        return f"/api/v2/resource/{parse.quote(self.resource_id, safe='')}/logs"

    def _get_paging_boundaries(self, dtos: List[ResourceHistory], sort_order: DatabaseOrder) -> PagingBoundaries:
        if sort_order.get_order() == "DESC":
            return PagingBoundaries(
                start=sort_order.ensure_boundary_type(dtos[0].dict()[sort_order.get_order_by_column_api_name()]),
                first_id=None,
                end=sort_order.ensure_boundary_type(dtos[-1].dict()[sort_order.get_order_by_column_api_name()]),
                last_id=None,
            )
        else:
            return PagingBoundaries(
                start=sort_order.ensure_boundary_type(dtos[-1].dict()[sort_order.get_order_by_column_api_name()]),
                first_id=None,
                end=sort_order.ensure_boundary_type(dtos[0].dict()[sort_order.get_order_by_column_api_name()]),
                last_id=None,
            )


class CompileReportPagingHandler(PagingHandler[CompileReport]):
    def __init__(
        self,
        counts_provider: PagingCountsProvider,
    ) -> None:
        super().__init__(counts_provider)

    def get_base_url(self) -> str:
        return "/api/v2/compilereport"

    def _get_paging_boundaries(self, dtos: List[CompileReport], sort_order: DatabaseOrder) -> PagingBoundaries:
        if sort_order.get_order() == "DESC":
            return PagingBoundaries(
                start=dtos[0].requested,
                first_id=dtos[0].id,
                end=dtos[-1].requested,
                last_id=dtos[-1].id,
            )
        else:
            return PagingBoundaries(
                start=dtos[-1].requested,
                first_id=dtos[-1].id,
                end=dtos[0].requested,
                last_id=dtos[0].id,
            )


class AgentPagingHandler(PagingHandler[AgentModel]):
    def get_base_url(self) -> str:
        return "/api/v2/agents"


class DesiredStateVersionPagingHandler(PagingHandler[DesiredStateVersion]):
    def get_base_url(self) -> str:
        return "/api/v2/desiredstate"

    def _get_paging_boundaries(self, dtos: List[DesiredStateVersion], sort_order: DatabaseOrder) -> PagingBoundaries:
        if sort_order.get_order() == "DESC":
            return PagingBoundaries(
                start=sort_order.ensure_boundary_type(dtos[0].dict()[sort_order.get_order_by_column_api_name()]),
                first_id=None,
                end=sort_order.ensure_boundary_type(dtos[-1].dict()[sort_order.get_order_by_column_api_name()]),
                last_id=None,
            )
        else:
            return PagingBoundaries(
                start=sort_order.ensure_boundary_type(dtos[-1].dict()[sort_order.get_order_by_column_api_name()]),
                first_id=None,
                end=sort_order.ensure_boundary_type(dtos[0].dict()[sort_order.get_order_by_column_api_name()]),
                last_id=None,
            )


class VersionedResourcePagingHandler(PagingHandler[VersionedResource]):
    def __init__(self, counts_provider: PagingCountsProvider, version: int) -> None:
        super().__init__(counts_provider)
        self.version = version

    def get_base_url(self) -> str:
        return f"/api/v2/desiredstate/{self.version}"

    def _get_paging_boundaries(self, dtos: List[VersionedResource], sort_order: DatabaseOrder) -> PagingBoundaries:
        if sort_order.get_order() == "DESC":
            return PagingBoundaries(
                start=sort_order.ensure_boundary_type(dtos[0].all_fields[sort_order.get_order_by_column_api_name()]),
                first_id=dtos[0].resource_version_id,
                end=sort_order.ensure_boundary_type(dtos[-1].all_fields[sort_order.get_order_by_column_api_name()]),
                last_id=dtos[-1].resource_version_id,
            )
        else:
            return PagingBoundaries(
                start=sort_order.ensure_boundary_type(dtos[-1].all_fields[sort_order.get_order_by_column_api_name()]),
                first_id=dtos[-1].resource_version_id,
                end=sort_order.ensure_boundary_type(dtos[0].all_fields[sort_order.get_order_by_column_api_name()]),
                last_id=dtos[0].resource_version_id,
            )
