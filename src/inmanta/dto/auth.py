"""
Copyright 2019 Inmanta

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
from enum import Enum
from typing import Optional

from pydantic import SerializationInfo, field_serializer

from inmanta import const
from inmanta.types import BaseModel as BaseModel


class AuthMethod(str, Enum):
    database = "database"
    oidc = "oidc"


class RoleAssignment(BaseModel):
    """
    :param environment: The environment scope of the role.
    :param role: The name of the role.
    """

    environment: uuid.UUID
    role: str


class RoleAssignmentsPerEnvironment(BaseModel):
    assignments: dict[uuid.UUID, list[str]]

    @field_serializer("assignments")
    def serialize_assignments(self, assignments: dict[uuid.UUID, list[str]], _info: SerializationInfo) -> dict[str, list[str]]:
        # Serialize uuid keys in dict to string. The json.dumps() doesn't use the custom serializer for that.
        # https://github.com/python/cpython/issues/63020
        return {str(k): v for k, v in assignments.items()}


class User(BaseModel):
    """A user"""

    username: str
    auth_method: AuthMethod
    is_admin: bool


class UserWithRoles(User):
    roles: dict[uuid.UUID, list[str]]

    @field_serializer("roles")
    def serialize_roles(self, roles: dict[uuid.UUID, list[str]], _info: SerializationInfo) -> dict[str, list[str]]:
        # Serialize uuid keys in dict to string. The json.dumps() doesn't use the custom serializer for that.
        # https://github.com/python/cpython/issues/63020
        return {str(k): v for k, v in roles.items()}


class Token(BaseModel):
    """A registered (revocable) authentication token, tracked in the token registry."""

    jti: uuid.UUID
    created_by: str | None = None
    client_types: list[const.ClientType] = []
    environment: uuid.UUID | None = None
    issued_at: datetime.datetime
    expires_at: datetime.datetime | None = None
    revoked_at: datetime.datetime | None = None
    last_used: datetime.datetime | None = None


class CurrentUser(BaseModel):
    """Information about the current logged in user"""

    username: str


class LoginReturn(BaseModel):
    """
    Login information

    :param token: A token representing the user's authentication session
    :param user: The user object for which the token was created
    :param expires_in: Lifetime of the token in seconds, or None when the token does not expire. Clients can use
                       this to renew the session before it expires.
    """

    token: str
    user: User
    expires_in: Optional[int] = None
