"""
Copyright 2026 Inmanta

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

# The database access layer lives in inmanta.data.dao. It is resolved lazily by __getattr__ below so that importing a
# lightweight sibling such as inmanta.data.model does not drag in sqlalchemy, asyncpg and inmanta.protocol. Python always
# executes this __init__ before any submodule of the package, so keep it free of expensive imports.
#
# Every name of inmanta.data.dao remains available as inmanta.data.<name>, both as an attribute and via
# `from inmanta.data import <name>`.

# flake8: noqa: F401
from typing import TYPE_CHECKING

_SUBMODULES = frozenset({"dao", "dataview", "model", "schema", "sqlalchemy"})

if TYPE_CHECKING:
    # Re-exported explicitly so that type checkers resolve these to their real types instead of falling back to __getattr__.
    # The non-dao imports at the end are names dao imports rather than defines, which callers still reach as
    # inmanta.data.<name>.
    from inmanta.data.dao import AGENT_AUTH as AGENT_AUTH
    from inmanta.data.dao import APILIMIT as APILIMIT
    from inmanta.data.dao import AUTO_DEPLOY as AUTO_DEPLOY
    from inmanta.data.dao import AUTO_FULL_COMPILE as AUTO_FULL_COMPILE
    from inmanta.data.dao import AUTOSTART_AGENT_DEPLOY_INTERVAL as AUTOSTART_AGENT_DEPLOY_INTERVAL
    from inmanta.data.dao import AUTOSTART_AGENT_REPAIR_INTERVAL as AUTOSTART_AGENT_REPAIR_INTERVAL
    from inmanta.data.dao import AUTOSTART_ON_START as AUTOSTART_ON_START
    from inmanta.data.dao import AVAILABLE_VERSIONS_TO_KEEP as AVAILABLE_VERSIONS_TO_KEEP
    from inmanta.data.dao import CORE_SCHEMA_NAME as CORE_SCHEMA_NAME
    from inmanta.data.dao import DBLIMIT as DBLIMIT
    from inmanta.data.dao import ENGINE as ENGINE
    from inmanta.data.dao import ENVIRONMENT_METRICS_RETENTION as ENVIRONMENT_METRICS_RETENTION
    from inmanta.data.dao import LOGGER as LOGGER
    from inmanta.data.dao import NOTIFICATION_RETENTION as NOTIFICATION_RETENTION
    from inmanta.data.dao import PACKAGE_WITH_UPDATE_FILES as PACKAGE_WITH_UPDATE_FILES
    from inmanta.data.dao import PRIMITIVE_SQL_TYPES as PRIMITIVE_SQL_TYPES
    from inmanta.data.dao import PROTECTED_ENVIRONMENT as PROTECTED_ENVIRONMENT
    from inmanta.data.dao import RECOMPILE_BACKOFF as RECOMPILE_BACKOFF
    from inmanta.data.dao import RESET_DEPLOY_PROGRESS_ON_START as RESET_DEPLOY_PROGRESS_ON_START
    from inmanta.data.dao import RESOURCE_ACTION_LOGS_RETENTION as RESOURCE_ACTION_LOGS_RETENTION
    from inmanta.data.dao import SERVER_COMPILE as SERVER_COMPILE
    from inmanta.data.dao import SESSION_FACTORY as SESSION_FACTORY
    from inmanta.data.dao import T_SELF as T_SELF
    from inmanta.data.dao import TYPE_MAP as TYPE_MAP
    from inmanta.data.dao import AbstractDatabaseOrderV2 as AbstractDatabaseOrderV2
    from inmanta.data.dao import Agent as Agent
    from inmanta.data.dao import AgentOrder as AgentOrder
    from inmanta.data.dao import ArgumentCollector as ArgumentCollector
    from inmanta.data.dao import BaseDocument as BaseDocument
    from inmanta.data.dao import BaseQueryBuilder as BaseQueryBuilder
    from inmanta.data.dao import BoolColumn as BoolColumn
    from inmanta.data.dao import CannotAssignRoleException as CannotAssignRoleException
    from inmanta.data.dao import ColumnNameStr as ColumnNameStr
    from inmanta.data.dao import ColumnType as ColumnType
    from inmanta.data.dao import Compile as Compile
    from inmanta.data.dao import CompileReportOrder as CompileReportOrder
    from inmanta.data.dao import ConfigurationModel as ConfigurationModel
    from inmanta.data.dao import DatabaseOrderV2 as DatabaseOrderV2
    from inmanta.data.dao import DataDocument as DataDocument
    from inmanta.data.dao import DateRangeConstraint as DateRangeConstraint
    from inmanta.data.dao import DateTimeColumn as DateTimeColumn
    from inmanta.data.dao import DesiredStateVersionOrder as DesiredStateVersionOrder
    from inmanta.data.dao import DiscoveredResource as DiscoveredResource
    from inmanta.data.dao import DiscoveredResourceOrder as DiscoveredResourceOrder
    from inmanta.data.dao import DocumentMeta as DocumentMeta
    from inmanta.data.dao import DryRun as DryRun
    from inmanta.data.dao import Environment as Environment
    from inmanta.data.dao import EnvironmentMetricsGauge as EnvironmentMetricsGauge
    from inmanta.data.dao import EnvironmentMetricsTimer as EnvironmentMetricsTimer
    from inmanta.data.dao import EnvironmentSettingsContainer as EnvironmentSettingsContainer
    from inmanta.data.dao import ExternalInitAsyncPG as ExternalInitAsyncPG
    from inmanta.data.dao import FactOrder as FactOrder
    from inmanta.data.dao import Field as Field
    from inmanta.data.dao import File as File
    from inmanta.data.dao import ForcedStringColumn as ForcedStringColumn
    from inmanta.data.dao import InvalidAttribute as InvalidAttribute
    from inmanta.data.dao import InvalidFieldNameException as InvalidFieldNameException
    from inmanta.data.dao import InvalidQueryParameter as InvalidQueryParameter
    from inmanta.data.dao import InvalidQueryType as InvalidQueryType
    from inmanta.data.dao import InvalidResourceSetMigration as InvalidResourceSetMigration
    from inmanta.data.dao import InvalidSort as InvalidSort
    from inmanta.data.dao import LogLine as LogLine
    from inmanta.data.dao import Notification as Notification
    from inmanta.data.dao import NotificationOrder as NotificationOrder
    from inmanta.data.dao import OptionalDateTimeColumn as OptionalDateTimeColumn
    from inmanta.data.dao import OptionalStringColumn as OptionalStringColumn
    from inmanta.data.dao import OrderStr as OrderStr
    from inmanta.data.dao import PagingCounts as PagingCounts
    from inmanta.data.dao import PagingOrder as PagingOrder
    from inmanta.data.dao import Parameter as Parameter
    from inmanta.data.dao import ParameterOrder as ParameterOrder
    from inmanta.data.dao import PartialBaseMissing as PartialBaseMissing
    from inmanta.data.dao import PositiveIntColumn as PositiveIntColumn
    from inmanta.data.dao import Project as Project
    from inmanta.data.dao import QueryFilter as QueryFilter
    from inmanta.data.dao import QueryType as QueryType
    from inmanta.data.dao import RangeConstraint as RangeConstraint
    from inmanta.data.dao import RangeOperator as RangeOperator
    from inmanta.data.dao import Report as Report
    from inmanta.data.dao import Resource as Resource
    from inmanta.data.dao import ResourceAction as ResourceAction
    from inmanta.data.dao import ResourceHistoryOrder as ResourceHistoryOrder
    from inmanta.data.dao import ResourceLogOrder as ResourceLogOrder
    from inmanta.data.dao import ResourcePersistentState as ResourcePersistentState
    from inmanta.data.dao import ResourceSet as ResourceSet
    from inmanta.data.dao import ResourceStatusOrder as ResourceStatusOrder
    from inmanta.data.dao import Role as Role
    from inmanta.data.dao import RoleStillAssignedException as RoleStillAssignedException
    from inmanta.data.dao import RowLockMode as RowLockMode
    from inmanta.data.dao import Scheduler as Scheduler
    from inmanta.data.dao import SchedulerSession as SchedulerSession
    from inmanta.data.dao import Setting as Setting
    from inmanta.data.dao import SimpleQueryBuilder as SimpleQueryBuilder
    from inmanta.data.dao import SingleDatabaseOrder as SingleDatabaseOrder
    from inmanta.data.dao import StringColumn as StringColumn
    from inmanta.data.dao import T as T
    from inmanta.data.dao import TableLockMode as TableLockMode
    from inmanta.data.dao import TablePrefixWrapper as TablePrefixWrapper
    from inmanta.data.dao import TBaseDocument as TBaseDocument
    from inmanta.data.dao import TextColumn as TextColumn
    from inmanta.data.dao import TransactionResult as TransactionResult
    from inmanta.data.dao import UnknownParameter as UnknownParameter
    from inmanta.data.dao import User as User
    from inmanta.data.dao import UUIDColumn as UUIDColumn
    from inmanta.data.dao import VersionedResourceOrder as VersionedResourceOrder
    from inmanta.data.dao import asyncpg_on_connect as asyncpg_on_connect
    from inmanta.data.dao import connect_pool as connect_pool
    from inmanta.data.dao import convert_agent_trigger_method as convert_agent_trigger_method
    from inmanta.data.dao import convert_boolean as convert_boolean
    from inmanta.data.dao import convert_int as convert_int
    from inmanta.data.dao import convert_positive_float as convert_positive_float
    from inmanta.data.dao import default_unset as default_unset
    from inmanta.data.dao import disconnect_pool as disconnect_pool
    from inmanta.data.dao import get_connection_pool as get_connection_pool
    from inmanta.data.dao import get_engine as get_engine
    from inmanta.data.dao import get_session as get_session
    from inmanta.data.dao import get_session_factory as get_session_factory
    from inmanta.data.dao import json_encode as json_encode
    from inmanta.data.dao import set_connection_pool as set_connection_pool
    from inmanta.data.dao import start_engine as start_engine
    from inmanta.data.dao import stop_engine as stop_engine
    from inmanta.data.dao import translate_to_postgres_type as translate_to_postgres_type
    from inmanta.data.dao import validate_cron as validate_cron
    from inmanta.data.dao import validate_cron_or_int as validate_cron_or_int
    from inmanta.data.model import AuthMethod as AuthMethod
    from inmanta.data.model import PipConfig as PipConfig
    from inmanta.data.sqlalchemy import AgentModules as AgentModules
    from inmanta.data.sqlalchemy import InmantaModule as InmantaModule
    from inmanta.data.sqlalchemy import ModuleFiles as ModuleFiles
    from inmanta.types import ResourceIdStr as ResourceIdStr


def __getattr__(name: str) -> object:
    # Submodules and dunders must not be resolved through dao: `from inmanta.data import dao` looks up "dao" on this
    # package first, which would come straight back here and recurse. Let the import system handle those itself.
    # Single underscore names are deliberately not excluded: dao._classes is reached this way.
    if name.startswith("__") or name in _SUBMODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    import importlib

    return getattr(importlib.import_module("inmanta.data.dao"), name)
