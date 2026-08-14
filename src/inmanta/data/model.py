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

# The data transfer objects moved to the inmanta.dto package, split into thematic modules. This module keeps every name
# importable from its historical location, which is what the stable API promises, but importing it executes inmanta/data/__init__.py
# and loads all of the DTOs. Prefer importing the one inmanta.dto submodule you need.

# flake8: noqa: F401

from inmanta.dto.agent import Agent as Agent
from inmanta.dto.agent import AgentName as AgentName
from inmanta.dto.agent import AgentProcess as AgentProcess
from inmanta.dto.auth import AuthMethod as AuthMethod
from inmanta.dto.auth import CurrentUser as CurrentUser
from inmanta.dto.auth import LoginReturn as LoginReturn
from inmanta.dto.auth import RoleAssignment as RoleAssignment
from inmanta.dto.auth import RoleAssignmentsPerEnvironment as RoleAssignmentsPerEnvironment
from inmanta.dto.auth import Token as Token
from inmanta.dto.auth import User as User
from inmanta.dto.auth import UserWithRoles as UserWithRoles
from inmanta.dto.code import InmantaModule as InmantaModule
from inmanta.dto.code import InmantaModuleName as InmantaModuleName
from inmanta.dto.code import InmantaModuleVersion as InmantaModuleVersion
from inmanta.dto.code import ModuleSource as ModuleSource
from inmanta.dto.code import ModuleSourceMetadata as ModuleSourceMetadata
from inmanta.dto.code import Source as Source
from inmanta.dto.compile import CompileData as CompileData
from inmanta.dto.compile import CompileDetails as CompileDetails
from inmanta.dto.compile import CompileReport as CompileReport
from inmanta.dto.compile import CompileRun as CompileRun
from inmanta.dto.compile import CompileRunBase as CompileRunBase
from inmanta.dto.compile import CompileRunReport as CompileRunReport
from inmanta.dto.desiredstate import DesiredStateLabel as DesiredStateLabel
from inmanta.dto.desiredstate import DesiredStateVersion as DesiredStateVersion
from inmanta.dto.desiredstate import ModelMetadata as ModelMetadata
from inmanta.dto.desiredstate import PromoteTriggerMethod as PromoteTriggerMethod
from inmanta.dto.diff import AttributeDiff as AttributeDiff
from inmanta.dto.diff import ResourceComplianceDiff as ResourceComplianceDiff
from inmanta.dto.diff import ResourceDiff as ResourceDiff
from inmanta.dto.diff import ResourceDiffStatus as ResourceDiffStatus
from inmanta.dto.discovery import DiscoveredResourceABC as DiscoveredResourceABC
from inmanta.dto.discovery import DiscoveredResourceInput as DiscoveredResourceInput
from inmanta.dto.discovery import DiscoveredResourceOutput as DiscoveredResourceOutput
from inmanta.dto.discovery import ResourceId as ResourceId
from inmanta.dto.dryrun import DryRun as DryRun
from inmanta.dto.dryrun import DryRunReport as DryRunReport
from inmanta.dto.environment import Environment as Environment
from inmanta.dto.environment import EnvironmentMetricsResult as EnvironmentMetricsResult
from inmanta.dto.environment import EnvironmentSetting as EnvironmentSetting
from inmanta.dto.environment import EnvironmentSettingDefinitionAPI as EnvironmentSettingDefinitionAPI
from inmanta.dto.environment import EnvironmentSettingDetails as EnvironmentSettingDetails
from inmanta.dto.environment import EnvironmentSettingsReponse as EnvironmentSettingsReponse
from inmanta.dto.environment import EnvSettingType as EnvSettingType
from inmanta.dto.environment import Project as Project
from inmanta.dto.environment import ProtectedBy as ProtectedBy
from inmanta.dto.log import LogLine as LogLine
from inmanta.dto.log import ResourceLog as ResourceLog
from inmanta.dto.notification import Notification as Notification
from inmanta.dto.paging import PagingBoundaries as PagingBoundaries
from inmanta.dto.parameter import Fact as Fact
from inmanta.dto.parameter import Parameter as Parameter
from inmanta.dto.pip import LEGACY_PIP_DEFAULT as LEGACY_PIP_DEFAULT
from inmanta.dto.pip import PipConfig as PipConfig
from inmanta.dto.pip import hyphenize as hyphenize
from inmanta.dto.resource import AttributeStateChange as AttributeStateChange
from inmanta.dto.resource import ComposedResourceSummary as ComposedResourceSummary
from inmanta.dto.resource import LatestReleasedResource as LatestReleasedResource
from inmanta.dto.resource import ReleasedResourceDetails as ReleasedResourceDetails
from inmanta.dto.resource import ReleasedResourceState as ReleasedResourceState
from inmanta.dto.resource import Resource as Resource
from inmanta.dto.resource import ResourceAction as ResourceAction
from inmanta.dto.resource import ResourceDeploySummary as ResourceDeploySummary
from inmanta.dto.resource import ResourceDetails as ResourceDetails
from inmanta.dto.resource import ResourceHistory as ResourceHistory
from inmanta.dto.resource import ResourceIdDetails as ResourceIdDetails
from inmanta.dto.resource import ResourceMinimal as ResourceMinimal
from inmanta.dto.resource import VersionedResource as VersionedResource
from inmanta.dto.resource import VersionedResourceDetails as VersionedResourceDetails
from inmanta.dto.scheduler import DataBaseReport as DataBaseReport
from inmanta.dto.scheduler import Discrepancy as Discrepancy
from inmanta.dto.scheduler import SchedulerStatusReport as SchedulerStatusReport
from inmanta.dto.status import ExtensionStatus as ExtensionStatus
from inmanta.dto.status import FeatureStatus as FeatureStatus
from inmanta.dto.status import ReportedStatus as ReportedStatus
from inmanta.dto.status import SliceStatus as SliceStatus
from inmanta.dto.status import StatusResponse as StatusResponse
from inmanta.types import BaseModel as BaseModel  # Keep in place for backwards compat with <=ISO8
from inmanta.types import ResourceIdStr as ResourceIdStr  # Keep in place for backwards compat with <=ISO8
from inmanta.types import ResourceType as ResourceType  # Keep in place for backwards compat with <=ISO8
from inmanta.types import ResourceVersionIdStr as ResourceVersionIdStr  # Keep in place for backwards compat with <=ISO8
