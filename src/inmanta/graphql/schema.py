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

import datetime
import typing
import uuid

import strawberry

EnvSettingType = str


@strawberry.type
class EnvironmentSetting:
    name: str
    type: str
    default: EnvSettingType
    doc: str
    recompile: bool
    update_model: bool
    agent_restart: bool
    allowed_values: list[EnvSettingType] | None = None


@strawberry.type
class Notification:
    id: uuid.UUID
    created: datetime.datetime
    title: str
    message: str
    severity: str
    uri: str | None
    read: bool
    cleared: bool


@strawberry.type
class Environment:

    @staticmethod
    def get_environments(id: uuid.UUID | None = strawberry.UNSET) -> list["Environment"]:
        prefix = "[get_environments]"
        _environments = [
            Environment(
                id=uuid.UUID("11111111-1234-5678-1234-000000000001"),
                name=f"{prefix} test-env-1",
                expert_mode_on=False,
                halted=False,
            ),
            Environment(
                id=uuid.UUID("11111111-1234-5678-1234-000000000002"),
                name=f"{prefix} test-env-2",
                expert_mode_on=True,
                halted=False,
            ),
        ]

        if id:
            return [environment for environment in _environments if environment.id == id]
        return _environments

    @strawberry.field
    def settings(self) -> list["EnvironmentSetting"]:
        return [
            EnvironmentSetting(
                name=f"setting for env {self.name}",
                type="str",
                default="default",
                recompile=False,
                update_model=False,
                agent_restart=False,
                doc="this is env_setting_1",
            )
        ]

    @strawberry.field
    def notifications(self) -> list[Notification]:
        notification_map = {
            uuid.UUID("11111111-1234-5678-1234-000000000002"): [
                Notification(
                    id=uuid.UUID("22222222-1234-5678-1234-000000000000"),
                    created=datetime.datetime.now(),
                    title="New notification",
                    message="This is a notification",
                    severity="message",
                    read=False,
                    cleared=False,
                    uri=None,
                ),
                Notification(
                    id=uuid.UUID("22222222-1234-5678-1234-000000000001"),
                    created=datetime.datetime.now(),
                    title="Another notification",
                    message="This is another notification",
                    severity="error",
                    read=False,
                    cleared=False,
                    uri=None,
                ),
            ]
        }
        return notification_map.get(self.id, [])

    id: uuid.UUID
    name: str
    description: str | None = None
    icon: str | None = None
    expert_mode_on: bool
    halted: bool


@strawberry.type
class Project:
    @staticmethod
    def get_projects(id: uuid.UUID | None = strawberry.UNSET) -> list["Project"]:
        prefix = "[get_projects]"
        _projects = [
            Project(
                id=uuid.UUID("00000000-1234-5678-1234-000000000001"),
                name=f"{prefix} test-proj-1",
            ),
            Project(
                id=uuid.UUID("00000000-1234-5678-1234-000000000002"),
                name=f"{prefix} test-proj-2",
            ),
        ]
        if id:
            return [project for project in _projects if project.id == id]
        return _projects

    @strawberry.field
    def environments(self) -> list[Environment]:
        prefix = "[projects.environments]"
        if self.id == uuid.UUID("00000000-1234-5678-1234-000000000001"):
            return [
                Environment(
                    id=uuid.UUID("11111111-1234-5678-1234-000000000001"),
                    name=f"{prefix} test-env-1",
                    expert_mode_on=False,
                    halted=False,
                ),
            ]
        if self.id == uuid.UUID("00000000-1234-5678-1234-000000000002"):
            return [
                Environment(
                    id=uuid.UUID("11111111-1234-5678-1234-000000000002"),
                    name=f"{prefix} test-env-2",
                    expert_mode_on=True,
                    halted=False,
                ),
                Environment(
                    id=uuid.UUID("11111111-1234-5678-1234-000000000003"),
                    name=f"{prefix} test-env-3",
                    expert_mode_on=True,
                    halted=False,
                ),
            ]
        return []

    id: uuid.UUID
    name: str


@strawberry.type
class Query:
    environments: typing.List[Environment] = strawberry.field(resolver=Environment.get_environments)
    projects: typing.List[Project] = strawberry.field(resolver=Project.get_projects)


schema = strawberry.Schema(query=Query)
