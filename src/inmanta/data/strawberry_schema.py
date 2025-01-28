import datetime
import typing
import uuid

import strawberry
"""
TODO
add filtering example

"""


"""
README

# Install strawberry
pip install 'strawberry-graphql=0.258.0'

# Run the GraphiQL server
cd work/inmanta/github-repos/inmanta-core/src/inmanta/data/
strawberry server strawberry_schema


# Sample queries:
{
  environments {
    id
    settings {
      name
      doc
      allowedValues
    }
    notifications {
      id
      created
      message
    }
  }
}

{
  projects {
    id
    name
    environments {
      id
      settings {
        name
      }
      notifications {
        id
        created
        title
        message
        severity
        uri
        read
        cleared
      }
      description
      expertModeOn
      halted
      icon
      name
    }
  }
}


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

def get_notifications_for_environment(root) -> list[Notification]:
    notification_map = {
        "11111111-1234-5678-1234-000000000002": [
            Notification(
                id="22222222-1234-5678-1234-000000000000",
                created = datetime.datetime.now(),
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
    return notification_map.get(root.id, [])


def get_settings_for_environment(root) -> list[EnvironmentSetting]:
    return [
        EnvironmentSetting(
            name=f"setting for env {root.name}",
            type="str",
            default="default",
            recompile=False,
            update_model=False,
            agent_restart=False,
            doc="this is env_setting_1",
        )
    ]


@strawberry.type
class Environment:
    id: uuid.UUID
    name: str
    description: str | None = None
    icon: str | None = None
    settings: list[EnvironmentSetting] = strawberry.field(resolver=get_settings_for_environment)
    notifications: list[Notification] = strawberry.field(resolver=get_notifications_for_environment)
    expert_mode_on: bool
    halted: bool



def get_environments():
    prefix = "[get_environments]"
    return [
        Environment(
            id="11111111-1234-5678-1234-000000000001",
            name=f"{prefix} test-env-1",
            expert_mode_on=False,
            halted=False
        ),
        Environment(
            id="11111111-1234-5678-1234-000000000002",
            name=f"{prefix} test-env-2",
            expert_mode_on=True,
            halted=False
        ),
    ]


def get_projects():
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


def get_environments_for_project(root) -> list[Environment]:
    prefix = "[get_environments_for_project]"
    if root.id == "00000000-1234-5678-1234-000000000001":
        return [
            Environment(
                id="11111111-1234-5678-1234-000000000001",
                name=f"{prefix} test-env-1",
                expert_mode_on=False,
                halted=False
            ),
        ]
    if root.id == "00000000-1234-5678-1234-000000000002":
        return [
            Environment(
            id="11111111-1234-5678-1234-000000000002",
            name=f"{prefix} test-env-2",
            expert_mode_on=True,
            halted=False,
            )
        ]
    return []


@strawberry.type
class Project:
    id: uuid.UUID
    name: str
    environments: list[Environment] = strawberry.field(resolver=get_environments_for_project)


@strawberry.type
class Query:
    environments: typing.List[Environment] = strawberry.field(resolver=get_environments)
    projects: typing.List[Project] = strawberry.field(resolver=get_projects)


schema = strawberry.Schema(query=Query)
