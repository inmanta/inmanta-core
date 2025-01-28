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
import inmanta.graphql.resolver


#
#
#
#
# @strawberry.type
# class Book:
#     title: str
#     author: str
#
#
# @strawberry.type
# class Query:
#     books: typing.List[Book] = strawberry.field(resolver=inmanta.graphql.resolver.get_books)

"""
TODO
add filtering example

"""

# EnvSettingType = Union[str, int] # Cant use union ??
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
    id: uuid.UUID
    name: str
    description: str | None = None
    icon: str | None = None
    settings: list[EnvironmentSetting] = strawberry.field(resolver=inmanta.graphql.resolver.get_settings_for_environment)
    notifications: list[Notification] = strawberry.field(resolver=inmanta.graphql.resolver.get_notifications_for_environment)
    expert_mode_on: bool
    halted: bool

@strawberry.type
class Project:
    id: uuid.UUID
    name: str
    environments: list[Environment] = strawberry.field(resolver=inmanta.graphql.resolver.get_environments_for_project)


@strawberry.type
class Query:
    environments: typing.List[Environment] = strawberry.field(resolver=inmanta.graphql.resolver.get_environments)
    projects: typing.List[Project] = strawberry.field(resolver=inmanta.graphql.resolver.get_projects)



