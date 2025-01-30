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

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EnvSettingType = str


class Base(DeclarativeBase):
    pass


class EnvironmentSetting(Base):
    __tablename__ = "environment_settings"
    name: Mapped[str] = mapped_column(String(30), primary_key=True)
    type: Mapped[str] = mapped_column(String(30))
    default: Mapped[EnvSettingType] = mapped_column(String(30))
    doc: Mapped[str] = mapped_column(String(200))
    recompile: Mapped[bool] = mapped_column(Boolean)
    update_model: Mapped[bool] = mapped_column(Boolean)
    agent_restart: Mapped[bool] = mapped_column(Boolean)
    # Trouble with list
    allowed_values: Mapped[str] = mapped_column(String(30), nullable=True)
    environment: Mapped["Environment"] = relationship(back_populates="settings")
    env_id: Mapped[str] = mapped_column(ForeignKey("environments.id"))

    def __repr__(self) -> str:
        return f"EnvironmentSetting(id={self.name!r})"


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(primary_key=True)
    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    title: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(String(300))
    severity: Mapped[str] = mapped_column(String(30))
    uri: Mapped[str | None] = mapped_column(String(30), nullable=True)
    read: Mapped[bool] = mapped_column(Boolean)
    cleared: Mapped[bool] = mapped_column(Boolean)
    environment: Mapped["Environment"] = relationship(back_populates="notifications")
    env_id: Mapped[str] = mapped_column(ForeignKey("environments.id"))

    def __repr__(self) -> str:
        return f"Notification(id={self.id!r}, name={self.title!r}, message={self.message!r})"


class Environment(Base):
    __tablename__ = "environments"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    # description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # icon: Mapped[str | None] = mapped_column(String(300), nullable=True)
    expert_mode_on: Mapped[bool] = mapped_column(Boolean)
    halted: Mapped[bool] = mapped_column(Boolean)

    notifications: Mapped[List["Notification"]] = relationship(back_populates="environment", cascade="all, delete-orphan")
    settings: Mapped[List["EnvironmentSetting"]] = relationship(back_populates="environment", cascade="all, delete-orphan")
    project: Mapped["Project"] = relationship(back_populates="environments")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))

    def __repr__(self) -> str:
        return f"Environment(id={self.id!r}, name={self.name!r}"


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    environments: Mapped[List["Environment"]] = relationship(back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Project(id={self.id!r}, name={self.name!r})"
