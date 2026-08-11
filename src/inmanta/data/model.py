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

# These data transfer objects moved to inmanta.dto, so that importing them no longer executes inmanta/data/__init__.py and
# with it the whole database layer. This module is kept as the historical, stable location. Prefer inmanta.dto in new code:
# importing inmanta.data.model necessarily loads the database layer, because Python executes a package __init__ before any
# of its submodules.

# flake8: noqa: F401
from inmanta.dto import LEGACY_PIP_DEFAULT as LEGACY_PIP_DEFAULT
from inmanta.dto import Agent as Agent
from inmanta.dto import AgentName as AgentName
from inmanta.dto import AgentProcess as AgentProcess
from inmanta.dto import AttributeDiff as AttributeDiff
from inmanta.dto import AttributeStateChange as AttributeStateChange
from inmanta.dto import AuthMethod as AuthMethod
from inmanta.dto import BaseModel as BaseModel
from inmanta.dto import CompileData as CompileData
from inmanta.dto import CompileDetails as CompileDetails
from inmanta.dto import CompileReport as CompileReport
from inmanta.dto import CompileRun as CompileRun
from inmanta.dto import CompileRunBase as CompileRunBase
from inmanta.dto import CompileRunReport as CompileRunReport
from inmanta.dto import ComposedResourceSummary as ComposedResourceSummary
from inmanta.dto import CurrentUser as CurrentUser
from inmanta.dto import DataBaseReport as DataBaseReport
from inmanta.dto import DesiredStateLabel as DesiredStateLabel
from inmanta.dto import DesiredStateVersion as DesiredStateVersion
from inmanta.dto import DiscoveredResourceABC as DiscoveredResourceABC
from inmanta.dto import DiscoveredResourceInput as DiscoveredResourceInput
from inmanta.dto import DiscoveredResourceOutput as DiscoveredResourceOutput
from inmanta.dto import Discrepancy as Discrepancy
from inmanta.dto import DryRun as DryRun
from inmanta.dto import DryRunReport as DryRunReport
from inmanta.dto import Environment as Environment
from inmanta.dto import EnvironmentMetricsResult as EnvironmentMetricsResult
from inmanta.dto import EnvironmentSetting as EnvironmentSetting
from inmanta.dto import EnvironmentSettingDefinitionAPI as EnvironmentSettingDefinitionAPI
from inmanta.dto import EnvironmentSettingDetails as EnvironmentSettingDetails
from inmanta.dto import EnvironmentSettingsReponse as EnvironmentSettingsReponse
from inmanta.dto import EnvSettingType as EnvSettingType
from inmanta.dto import ExtensionStatus as ExtensionStatus
from inmanta.dto import Fact as Fact
from inmanta.dto import FeatureStatus as FeatureStatus
from inmanta.dto import InmantaModule as InmantaModule
from inmanta.dto import InmantaModuleName as InmantaModuleName
from inmanta.dto import InmantaModuleVersion as InmantaModuleVersion
from inmanta.dto import LatestReleasedResource as LatestReleasedResource
from inmanta.dto import LoginReturn as LoginReturn
from inmanta.dto import LogLine as LogLine
from inmanta.dto import ModelMetadata as ModelMetadata
from inmanta.dto import ModuleSource as ModuleSource
from inmanta.dto import ModuleSourceMetadata as ModuleSourceMetadata
from inmanta.dto import Notification as Notification
from inmanta.dto import PagingBoundaries as PagingBoundaries
from inmanta.dto import Parameter as Parameter
from inmanta.dto import PipConfig as PipConfig
from inmanta.dto import Project as Project
from inmanta.dto import PromoteTriggerMethod as PromoteTriggerMethod
from inmanta.dto import ProtectedBy as ProtectedBy
from inmanta.dto import ReleasedResourceDetails as ReleasedResourceDetails
from inmanta.dto import ReleasedResourceState as ReleasedResourceState
from inmanta.dto import ReportedStatus as ReportedStatus
from inmanta.dto import Resource as Resource
from inmanta.dto import ResourceAction as ResourceAction
from inmanta.dto import ResourceComplianceDiff as ResourceComplianceDiff
from inmanta.dto import ResourceDeploySummary as ResourceDeploySummary
from inmanta.dto import ResourceDetails as ResourceDetails
from inmanta.dto import ResourceDiff as ResourceDiff
from inmanta.dto import ResourceDiffStatus as ResourceDiffStatus
from inmanta.dto import ResourceHistory as ResourceHistory
from inmanta.dto import ResourceId as ResourceId
from inmanta.dto import ResourceIdDetails as ResourceIdDetails
from inmanta.dto import ResourceIdStr as ResourceIdStr
from inmanta.dto import ResourceLog as ResourceLog
from inmanta.dto import ResourceMinimal as ResourceMinimal
from inmanta.dto import ResourceType as ResourceType
from inmanta.dto import ResourceVersionIdStr as ResourceVersionIdStr
from inmanta.dto import RoleAssignment as RoleAssignment
from inmanta.dto import RoleAssignmentsPerEnvironment as RoleAssignmentsPerEnvironment
from inmanta.dto import SchedulerStatusReport as SchedulerStatusReport
from inmanta.dto import SliceStatus as SliceStatus
from inmanta.dto import Source as Source
from inmanta.dto import StatusResponse as StatusResponse
from inmanta.dto import Token as Token
from inmanta.dto import User as User
from inmanta.dto import UserWithRoles as UserWithRoles
from inmanta.dto import VersionedResource as VersionedResource
from inmanta.dto import VersionedResourceDetails as VersionedResourceDetails
from inmanta.dto import hyphenize as hyphenize
