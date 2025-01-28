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
from typing import List

import inmanta.graphql.schema
from inmanta.graphql.schema import Notification, Environment, EnvironmentSetting, Project


def get_books() -> List[inmanta.graphql.schema.Book]:
    return [
        inmanta.graphql.schema.Book(
            title="The Great Gatsby",
            author="F. Scott Fitzgerald",
        ),
    ]

def get_notifications_for_environment(root) -> list[Notification]:
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


def get_environments():
    prefix = "[get_environments]"
    return [
        Environment(id="11111111-1234-5678-1234-000000000001", name=f"{prefix} test-env-1", expert_mode_on=False, halted=False),
        Environment(id="11111111-1234-5678-1234-000000000002", name=f"{prefix} test-env-2", expert_mode_on=True, halted=False),
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
                id="11111111-1234-5678-1234-000000000001", name=f"{prefix} test-env-1", expert_mode_on=False, halted=False
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
