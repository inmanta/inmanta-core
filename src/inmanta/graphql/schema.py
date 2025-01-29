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

<<<<<<< Updated upstream
=======
#
#
# @strawberry.type
# class Book:
#     title: str
#     author: str
#
# @strawberry.type
# class Query:
#     books: typing.List[Book] = strawberry.field(resolver=inmanta.graphql.resolver.get_books)



>>>>>>> Stashed changes
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

# """
# TODO
# add filtering example
#
# """
#
#
# """
# README
#
# # Install strawberry
# pip install 'strawberry-graphql=0.258.0'
#
# # Run the GraphiQL server
# cd work/inmanta/github-repos/inmanta-core/src/inmanta/data/

# add this line:
# schema = strawberry.Schema(query=Query)

# in cli:
# strawberry server schema
#
#
# # Sample queries:
# {
#   environments {
#     id
#     settings {
#       name
#       doc
#       allowedValues
#     }
#     notifications {
#       id
#       created
#       message
#     }
#   }
# }
#
# {
#   projects {
#     id
#     name
#     environments {
#       id
#       settings {
#         name
#       }
#       notifications {
#         id
#         created
#         title
#         message
#         severity
#         uri
#         read
#         cleared
#       }
#       description
#       expertModeOn
#       halted
#       icon
#       name
#     }
#   }
# }
#
#
# """
#
#
#
#










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

<<<<<<< Updated upstream
@strawberry.type
class Environment:
=======

@strawberry.type
class Environment:

    @staticmethod
    def get_environments() -> list["Environment"]:
        prefix = "[get_environments]"
        return [
            Environment(id="11111111-1234-5678-1234-000000000001", name=f"{prefix} test-env-1", expert_mode_on=False,
                        halted=False),
            Environment(id="11111111-1234-5678-1234-000000000002", name=f"{prefix} test-env-2", expert_mode_on=True,
                        halted=False),
        ]
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
            "11111111-1234-5678-1234-000000000002": [
                Notification(
                    id="22222222-1234-5678-1234-000000000000",
                    created=datetime.datetime.now(),
                    title="New notification",
                    message="This is a notification",
                    severity="message",
                    read=False,
                    cleared=False,
                    uri=None,
                ),
                Notification(
                    id="22222222-1234-5678-1234-000000000001",
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

>>>>>>> Stashed changes
    id: uuid.UUID
    name: str
    description: str | None = None
    icon: str | None = None
<<<<<<< Updated upstream
    settings: list[EnvironmentSetting] = strawberry.field(resolver=inmanta.graphql.resolver.get_settings_for_environment)
    notifications: list[Notification] = strawberry.field(resolver=inmanta.graphql.resolver.get_notifications_for_environment)
=======
>>>>>>> Stashed changes
    expert_mode_on: bool
    halted: bool

@strawberry.type
class Project:
<<<<<<< Updated upstream
    id: uuid.UUID
    name: str
    environments: list[Environment] = strawberry.field(resolver=inmanta.graphql.resolver.get_environments_for_project)
=======
    @staticmethod
    def get_projects() -> list["Project"]:
        prefix = "[get_projects]"
        return [
            Project(
                id="00000000-1234-5678-1234-000000000001",
                name=f"{prefix} test-proj-1",
            ),
            Project(
                id="00000000-1234-5678-1234-000000000002",
                name=f"{prefix} test-proj-2",
            ),
        ]

    @strawberry.field
    def environments(self) -> list[Environment]:
        prefix = "[get_environments_for_project]"
        if self.id == "00000000-1234-5678-1234-000000000001":
            return [
                Environment(
                    id="11111111-1234-5678-1234-000000000001", name=f"{prefix} test-env-1", expert_mode_on=False, halted=False
                ),
            ]
        if self.id == "00000000-1234-5678-1234-000000000002":
            return [
                Environment(
                    id="11111111-1234-5678-1234-000000000002",
                    name=f"{prefix} test-env-2",
                    expert_mode_on=True,
                    halted=False,
                )
            ]
        return []

    id: uuid.UUID
    name: str
>>>>>>> Stashed changes


@strawberry.type
class Query:
<<<<<<< Updated upstream
    environments: typing.List[Environment] = strawberry.field(resolver=inmanta.graphql.resolver.get_environments)
    projects: typing.List[Project] = strawberry.field(resolver=inmanta.graphql.resolver.get_projects)



=======
    environments: typing.List[Environment] = strawberry.field(resolver=Environment.get_environments)
    projects: typing.List[Project] = strawberry.field(resolver=Project.get_projects)


schema = strawberry.Schema(query=Query)
>>>>>>> Stashed changes
