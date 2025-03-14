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
import uuid
from typing import Any, List, Optional

from inmanta.data.model import EnvSettingType
from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    DateTime,
    Double,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Currently, these models don't offer any additional validation, besides typing, so it's best to avoid inserting/modifying
# DB entries directly using these models.


class Base(DeclarativeBase):
    pass


class Module(Base):
    __tablename__ = "module"

    __table_args__ = (
        PrimaryKeyConstraint("name", "version", "environment", name="module_pkey"),
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="code_environment_fkey"),
    )

    name: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    environment: Mapped[uuid.UUID] = mapped_column(UUID)
    requirements: Mapped[list[str]] = mapped_column(ARRAY(String()))


class FilesInModule(Base):
    __tablename__ = "files_in_module"
    __table_args__ = (
        ForeignKeyConstraint(
            ["module_name", "module_version", "environment"],
            ["module.name", "module.version", "module.environment"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="files_in_module_environment_fkey"),
        ForeignKeyConstraint(
            ["file_content_hash"], ["file.content_hash"], ondelete="RESTRICT", name="files_in_module_file_content_hash_fkey"
        ),  # todo add test for restrict behaviour on delete
        UniqueConstraint("module_name", "module_version", "environment", "file_path"),
    )
    __mapper_args__ = {"primary_key": ["module_name", "module_version", "environment", "file_path"]}

    module_name: Mapped[str] = mapped_column(String)
    module_version: Mapped[str] = mapped_column(String)
    environment: Mapped[uuid.UUID] = mapped_column(UUID)
    file_content_hash: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)


class ModulesForAgent(Base):
    __tablename__ = "modules_for_agent"
    __table_args__ = (
        ForeignKeyConstraint(
            ["cm_version", "environment"], ["configurationmodel.version", "configurationmodel.environment"], ondelete="CASCADE"
        ),  # TODO add test for deletion: check this deleted when cm is deleted via regular api (non-sqlalchemy api)
        ForeignKeyConstraint(["agent_name", "environment"], ["agent.name", "agent.environment"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["module_name", "module_version", "environment"],
            ["module.name", "module.version", "module.environment"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("cm_version", "environment", "agent_name", "module_name"),
    )
    __mapper_args__ = {"primary_key": ["cm_version", "environment", "agent_name", "module_name"]}

    cm_version: Mapped[int] = mapped_column(Integer)
    environment: Mapped[uuid.UUID] = mapped_column(UUID)
    agent_name: Mapped[str] = mapped_column(String)
    module_name: Mapped[str] = mapped_column(String)
    module_version: Mapped[str] = mapped_column(String)


class File(Base):
    __tablename__ = "file"
    __table_args__ = (PrimaryKeyConstraint("content_hash", name="file_pkey"),)

    content_hash: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)


class InmantaUser(Base):
    __tablename__ = "inmanta_user"
    __table_args__ = (PrimaryKeyConstraint("id", name="user_pkey"), UniqueConstraint("username", name="user_username_key"))

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    username: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    auth_method: Mapped[str] = mapped_column(Enum("database", "oidc", name="auth_method"))


class Project(Base):
    __tablename__ = "project"
    __table_args__ = (PrimaryKeyConstraint("id", name="project_pkey"), UniqueConstraint("name", name="project_name_key"))

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String)

    environment: Mapped[List["Environment"]] = relationship("Environment", back_populates="project_")


class Schemamanager(Base):
    __tablename__ = "schemamanager"
    __table_args__ = (PrimaryKeyConstraint("name", name="schemamanager_pkey"),)

    name: Mapped[str] = mapped_column(String, primary_key=True)
    installed_versions: Mapped[Optional[list[int]]] = mapped_column(ARRAY(Integer()))


class Environment(Base):
    __tablename__ = "environment"
    __table_args__: Any = (
        ForeignKeyConstraint(["project"], ["project.id"], ondelete="CASCADE", name="environment_project_fkey"),
        PrimaryKeyConstraint("id", name="environment_pkey"),
        Index("environment_name_project_index", "project", "name", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    project: Mapped[uuid.UUID] = mapped_column(UUID)
    halted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    repo_url: Mapped[Optional[str]] = mapped_column(String, server_default=text("''::character varying"))
    repo_branch: Mapped[Optional[str]] = mapped_column(String, server_default=text("''::character varying"))
    settings: Mapped[Optional[dict[str, EnvSettingType]]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    last_version: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"))
    description: Mapped[Optional[str]] = mapped_column(String(255), server_default=text("''::character varying"))
    icon: Mapped[Optional[str]] = mapped_column(String(65535), server_default=text("''::character varying"))
    is_marked_for_deletion: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))

    project_: Mapped["Project"] = relationship("Project", back_populates="environment")

    agentprocess: Mapped[List["AgentProcess"]] = relationship("AgentProcess", back_populates="environment_")
    code: Mapped[List["Code"]] = relationship("Code", back_populates="environment_")
    compile: Mapped[List["Compile"]] = relationship("Compile", back_populates="environment_")
    configurationmodel: Mapped[List["ConfigurationModel"]] = relationship("ConfigurationModel", back_populates="environment_")
    discoveredresource: Mapped[List["DiscoveredResource"]] = relationship("DiscoveredResource", back_populates="environment_")
    environmentmetricsgauge: Mapped[List["EnvironmentMetricsGauge"]] = relationship(
        "EnvironmentMetricsGauge", back_populates="environment_"
    )
    environmentmetricstimer: Mapped[List["EnvironmentMetricsTimer"]] = relationship(
        "EnvironmentMetricsTimer", back_populates="environment_"
    )
    notification: Mapped[List["Notification"]] = relationship("Notification", back_populates="environment_")
    parameter: Mapped[List["Parameter"]] = relationship("Parameter", back_populates="environment_")
    resource_persistent_state: Mapped[List["ResourcePersistentState"]] = relationship(
        "ResourcePersistentState", back_populates="environment_"
    )
    unknownparameter: Mapped[List["UnknownParameter"]] = relationship("UnknownParameter", back_populates="environment_")
    agent: Mapped[List["Agent"]] = relationship("Agent", back_populates="environment_")


class AgentProcess(Base):
    __tablename__ = "agentprocess"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="agentprocess_environment_fkey"),
        PrimaryKeyConstraint("sid", name="agentprocess_pkey"),
        Index("agentprocess_env_expired_index", "environment", "expired"),
        Index("agentprocess_env_hostname_expired_index", "environment", "hostname", "expired"),
        Index("agentprocess_expired_index", "expired"),
        Index("agentprocess_sid_expired_index", "sid", "expired", unique=True),
    )

    hostname: Mapped[str] = mapped_column(String)
    environment: Mapped[uuid.UUID] = mapped_column(UUID)
    sid: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    first_seen: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    last_seen: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    expired: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="agentprocess")
    agentinstance: Mapped[List["AgentInstance"]] = relationship("AgentInstance", back_populates="agentprocess")


class Code(Base):
    __tablename__ = "code"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="code_environment_fkey"),
        PrimaryKeyConstraint("environment", "version", "resource", name="code_pkey"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    resource: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_refs: Mapped[Optional[dict[str, tuple[str, str, list[str]]]]] = mapped_column(JSONB)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="code")


class Compile(Base):
    __tablename__ = "compile"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="compile_environment_fkey"),
        ForeignKeyConstraint(
            ["substitute_compile_id"], ["compile.id"], ondelete="CASCADE", name="compile_substitute_compile_id_fkey"
        ),
        PrimaryKeyConstraint("id", name="compile_pkey"),
        Index("compile_completed_environment_idx", "completed", "environment"),
        Index("compile_env_remote_id_index", "environment", "remote_id"),
        Index("compile_env_requested_index", "environment", "requested"),
        Index("compile_env_started_index", "environment", "started"),
        Index("compile_environment_version_index", "environment", "version"),
        Index("compile_substitute_compile_id_index", "substitute_compile_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    environment: Mapped[uuid.UUID] = mapped_column(UUID)
    requested_environment_variables: Mapped[dict[str, str]] = mapped_column(JSONB)
    mergeable_environment_variables: Mapped[dict[str, str]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    soft_delete: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    started: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    completed: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    requested: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB)
    do_export: Mapped[Optional[bool]] = mapped_column(Boolean)
    force_update: Mapped[Optional[bool]] = mapped_column(Boolean)
    success: Mapped[Optional[bool]] = mapped_column(Boolean)
    version: Mapped[Optional[int]] = mapped_column(Integer)
    remote_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID)
    handled: Mapped[Optional[bool]] = mapped_column(Boolean)
    substitute_compile_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID)
    compile_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    partial: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))
    removed_resource_sets: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String()), server_default=text("ARRAY[]::character varying[]")
    )
    notify_failed_compile: Mapped[Optional[bool]] = mapped_column(Boolean)
    failed_compile_message: Mapped[Optional[str]] = mapped_column(String)
    exporter_plugin: Mapped[Optional[str]] = mapped_column(String)
    used_environment_variables: Mapped[Optional[dict[str, str]]] = mapped_column(JSONB)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="compile")
    substitute_compile: Mapped["Compile"] = relationship(
        "Compile", remote_side=[id], back_populates="substitute_compile_reverse"
    )
    substitute_compile_reverse: Mapped[List["Compile"]] = relationship(
        "Compile", remote_side=[substitute_compile_id], back_populates="substitute_compile"
    )
    report: Mapped[List["Report"]] = relationship("Report", back_populates="compile_")


class ConfigurationModel(Base):
    __tablename__ = "configurationmodel"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment"], ["environment.id"], ondelete="CASCADE", name="configurationmodel_environment_fkey"
        ),
        PrimaryKeyConstraint("environment", "version", name="configurationmodel_pkey"),
        Index("configurationmodel_env_released_version_index", "environment", "released", "version", unique=True),
        Index("configurationmodel_env_version_total_index", "environment", "version", "total", unique=True),
    )

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    undeployable: Mapped[list[str]] = mapped_column(ARRAY(String()))
    skipped_for_undeployable: Mapped[list[str]] = mapped_column(ARRAY(String()))
    is_suitable_for_partial_compiles: Mapped[bool] = mapped_column(Boolean)
    date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    released: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))
    version_info: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    total: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"))
    partial_base: Mapped[Optional[int]] = mapped_column(Integer)
    pip_config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="configurationmodel")
    dryrun: Mapped[List["Dryrun"]] = relationship("Dryrun", back_populates="configurationmodel")
    resource: Mapped[List["Resource"]] = relationship("Resource", back_populates="configurationmodel")
    resourceaction: Mapped[List["ResourceAction"]] = relationship("ResourceAction", back_populates="configurationmodel")
    unknownparameter: Mapped[List["UnknownParameter"]] = relationship("UnknownParameter", back_populates="configurationmodel")


class DiscoveredResource(Base):
    __tablename__ = "discoveredresource"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment"], ["environment.id"], ondelete="CASCADE", name="unmanagedresource_environment_fkey"
        ),
        PrimaryKeyConstraint("environment", "discovered_resource_id", name="discoveredresource_pkey"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    discovered_resource_id: Mapped[str] = mapped_column(String, primary_key=True)
    values: Mapped[dict[str, Any]] = mapped_column(JSONB)
    discovered_at: Mapped[datetime.datetime] = mapped_column(DateTime(True))
    discovery_resource_id: Mapped[Optional[str]] = mapped_column(String)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="discoveredresource")


class EnvironmentMetricsGauge(Base):
    __tablename__ = "environmentmetricsgauge"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment"], ["environment.id"], ondelete="CASCADE", name="environmentmetricsgauge_environment_fkey"
        ),
        PrimaryKeyConstraint("environment", "timestamp", "metric_name", "category", name="environmentmetricsgauge_pkey"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    metric_name: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(True), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String, primary_key=True, server_default=text("'__None__'::character varying"))

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="environmentmetricsgauge")


class EnvironmentMetricsTimer(Base):
    __tablename__ = "environmentmetricstimer"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment"], ["environment.id"], ondelete="CASCADE", name="environmentmetricstimer_environment_fkey"
        ),
        PrimaryKeyConstraint("environment", "timestamp", "metric_name", "category", name="environmentmetricstimer_pkey"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    metric_name: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(True), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    value: Mapped[float] = mapped_column(Double(53))
    category: Mapped[str] = mapped_column(String, primary_key=True, server_default=text("'__None__'::character varying"))

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="environmentmetricstimer")


class Notification(Base):
    __tablename__ = "notification"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="notification_environment_fkey"),
        PrimaryKeyConstraint("environment", "id", name="notification_pkey"),
        Index("notification_env_created_id_index", "environment", "created", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    created: Mapped[datetime.datetime] = mapped_column(DateTime(True))
    title: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    read: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    cleared: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    severity: Mapped[Optional[str]] = mapped_column(
        Enum("message", "info", "success", "warning", "error", name="notificationseverity"),
        server_default=text("'message'::notificationseverity"),
    )
    uri: Mapped[Optional[str]] = mapped_column(String)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="notification")


class Parameter(Base):
    __tablename__ = "parameter"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="parameter_environment_fkey"),
        PrimaryKeyConstraint("id", name="parameter_pkey"),
        Index("parameter_env_name_resource_id_index", "environment", "name", "resource_id"),
        Index("parameter_environment_resource_id_index", "environment", "resource_id"),
        Index("parameter_metadata_index", "metadata"),
        Index("parameter_updated_index", "updated"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String, server_default=text("''::character varying"))
    environment: Mapped[uuid.UUID] = mapped_column(UUID)
    source: Mapped[str] = mapped_column(String)
    expires: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    resource_id: Mapped[Optional[str]] = mapped_column(String, server_default=text("''::character varying"))
    updated: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="parameter")


class ResourcePersistentState(Base):
    __tablename__ = "resource_persistent_state"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment"], ["environment.id"], ondelete="CASCADE", name="resource_persistent_state_environment_fkey"
        ),
        PrimaryKeyConstraint("environment", "resource_id", name="resource_persistent_state_pkey"),
        Index("resource_persistent_state_environment_agent_resource_id_idx", "environment", "agent", "resource_id"),
        Index(
            "resource_persistent_state_environment_resource_id_value_res_idx", "environment", "resource_id_value", "resource_id"
        ),
        Index("resource_persistent_state_environment_resource_type_resourc_idx", "environment", "resource_type", "resource_id"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    resource_id: Mapped[str] = mapped_column(String, primary_key=True)
    last_non_deploying_status: Mapped[str] = mapped_column(
        Enum(
            "unavailable",
            "skipped",
            "dry",
            "deployed",
            "failed",
            "available",
            "cancelled",
            "undefined",
            "skipped_for_undefined",
            name="non_deploying_resource_state",
        ),
        server_default=text("'available'::non_deploying_resource_state"),
    )
    resource_type: Mapped[str] = mapped_column(String)
    agent: Mapped[str] = mapped_column(String)
    resource_id_value: Mapped[str] = mapped_column(String)
    is_undefined: Mapped[bool] = mapped_column(Boolean)
    is_orphan: Mapped[bool] = mapped_column(Boolean)
    last_deploy_result: Mapped[str] = mapped_column(String)
    blocked: Mapped[str] = mapped_column(String)
    last_deploy: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    last_success: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    last_produced_events: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    last_deployed_attribute_hash: Mapped[Optional[str]] = mapped_column(String)
    last_deployed_version: Mapped[Optional[int]] = mapped_column(Integer)
    current_intent_attribute_hash: Mapped[Optional[str]] = mapped_column(String)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="resource_persistent_state")


class Scheduler(Environment):
    __tablename__ = "scheduler"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="scheduler_environment_fkey"),
        PrimaryKeyConstraint("environment", name="scheduler_pkey"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    last_processed_model_version: Mapped[Optional[int]] = mapped_column(Integer)


class AgentInstance(Base):
    __tablename__ = "agentinstance"
    __table_args__ = (
        ForeignKeyConstraint(["process"], ["agentprocess.sid"], ondelete="CASCADE", name="agentinstance_process_fkey"),
        PrimaryKeyConstraint("id", name="agentinstance_pkey"),
        UniqueConstraint("tid", "process", "name", name="agentinstance_unique"),
        Index("agentinstance_expired_index", "expired"),
        Index("agentinstance_expired_tid_endpoint_index", "tid", "name", "expired"),
        Index("agentinstance_process_index", "process"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    process: Mapped[uuid.UUID] = mapped_column(UUID)
    name: Mapped[str] = mapped_column(String)
    tid: Mapped[uuid.UUID] = mapped_column(UUID)
    expired: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    agentprocess: Mapped["AgentProcess"] = relationship("AgentProcess", back_populates="agentinstance")
    agent: Mapped[List["Agent"]] = relationship("Agent", back_populates="agentinstance")


class Dryrun(Base):
    __tablename__ = "dryrun"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment", "model"],
            ["configurationmodel.environment", "configurationmodel.version"],
            ondelete="CASCADE",
            name="dryrun_environment_model_fkey",
        ),
        PrimaryKeyConstraint("id", name="dryrun_pkey"),
        Index("dryrun_env_model_index", "environment", "model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    environment: Mapped[uuid.UUID] = mapped_column(UUID)
    model: Mapped[int] = mapped_column(Integer)
    date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    total: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"))
    todo: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"))
    resources: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    configurationmodel: Mapped["ConfigurationModel"] = relationship("ConfigurationModel", back_populates="dryrun")


class Report(Base):
    __tablename__ = "report"
    __table_args__ = (
        ForeignKeyConstraint(["compile"], ["compile.id"], ondelete="CASCADE", name="report_compile_fkey"),
        PrimaryKeyConstraint("id", name="report_pkey"),
        Index("report_compile_index", "compile"),
        Index("report_started_compile_returncode", "compile", "returncode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    started: Mapped[datetime.datetime] = mapped_column(DateTime(True))
    command: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    compile: Mapped[uuid.UUID] = mapped_column(UUID)
    completed: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    errstream: Mapped[Optional[str]] = mapped_column(String, server_default=text("''::character varying"))
    outstream: Mapped[Optional[str]] = mapped_column(String, server_default=text("''::character varying"))
    returncode: Mapped[Optional[int]] = mapped_column(Integer)

    compile_: Mapped["Compile"] = relationship("Compile", back_populates="report")


class Resource(Base):
    __tablename__ = "resource"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment", "model"],
            ["configurationmodel.environment", "configurationmodel.version"],
            ondelete="CASCADE",
            name="resource_environment_model_fkey",
        ),
        PrimaryKeyConstraint("environment", "model", "resource_id", name="resource_pkey"),
        Index("resource_attributes_index", "attributes"),
        Index("resource_env_attr_hash_index", "environment", "attribute_hash"),
        Index("resource_env_model_agent_index", "environment", "model", "agent"),
        Index("resource_env_resourceid_index", "environment", "resource_id", "model", unique=True),
        Index("resource_environment_agent_idx", "environment", "agent"),
        Index("resource_environment_model_resource_set_idx", "environment", "model", "resource_set"),
        Index("resource_environment_model_resource_type_idx", "environment", "model", "resource_type", "resource_id_value"),
        Index("resource_environment_resource_id_value_index", "environment", "resource_id_value"),
        Index("resource_environment_resource_type_index", "environment", "resource_type"),
        Index("resource_environment_status_model_idx", "environment", "status", "model"),
        Index("resource_resource_id_index", "resource_id"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    model: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_id: Mapped[str] = mapped_column(String, primary_key=True)
    agent: Mapped[str] = mapped_column(String)
    resource_type: Mapped[str] = mapped_column(String)
    resource_id_value: Mapped[str] = mapped_column(String)
    attributes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    attribute_hash: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[Optional[str]] = mapped_column(
        Enum(
            "unavailable",
            "skipped",
            "dry",
            "deployed",
            "failed",
            "deploying",
            "available",
            "cancelled",
            "undefined",
            "skipped_for_undefined",
            name="resourcestate",
        ),
        server_default=text("'available'::resourcestate"),
    )
    provides: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String()), server_default=text("ARRAY[]::character varying[]"))
    resource_set: Mapped[Optional[str]] = mapped_column(String)

    configurationmodel: Mapped["ConfigurationModel"] = relationship("ConfigurationModel", back_populates="resource")
    resource_action: Mapped[List["ResourceAction"]] = relationship(
        "ResourceAction", secondary="resourceaction_resource", back_populates="resource"
    )


class ResourceAction(Base):
    __tablename__ = "resourceaction"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment", "version"],
            ["configurationmodel.environment", "configurationmodel.version"],
            ondelete="CASCADE",
            name="resourceaction_environment_version_fkey",
        ),
        PrimaryKeyConstraint("action_id", name="resourceaction_pkey"),
        Index("resourceaction_environment_action_started_index", "environment", "action", "started"),
        Index("resourceaction_environment_version_started_index", "environment", "version", "started"),
        Index("resourceaction_started_index", "started"),
    )

    action_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    action: Mapped[str] = mapped_column(
        Enum("store", "push", "pull", "deploy", "dryrun", "getfact", "other", name="resourceaction_type")
    )
    started: Mapped[datetime.datetime] = mapped_column(DateTime(True))
    environment: Mapped[uuid.UUID] = mapped_column(UUID)
    version: Mapped[int] = mapped_column(Integer)
    resource_version_ids: Mapped[list[str]] = mapped_column(ARRAY(String()))
    finished: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    messages: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(ARRAY(JSONB))
    status: Mapped[Optional[str]] = mapped_column(
        Enum(
            "unavailable",
            "skipped",
            "dry",
            "deployed",
            "failed",
            "deploying",
            "available",
            "cancelled",
            "undefined",
            "skipped_for_undefined",
            name="resourcestate",
        ),
        server_default=text("'available'::resourcestate"),
    )
    changes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    change: Mapped[Optional[str]] = mapped_column(Enum("nochange", "created", "purged", "updated", name="change"))

    resource: Mapped[List["Resource"]] = relationship(
        "Resource", secondary="resourceaction_resource", back_populates="resource_action"
    )
    configurationmodel: Mapped["ConfigurationModel"] = relationship("ConfigurationModel", back_populates="resourceaction")


class UnknownParameter(Base):
    __tablename__ = "unknownparameter"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment", "version"],
            ["configurationmodel.environment", "configurationmodel.version"],
            ondelete="CASCADE",
            name="unknownparameter_environment_version_fkey",
        ),
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="unknownparameter_environment_fkey"),
        PrimaryKeyConstraint("id", name="unknownparameter_pkey"),
        Index("unknownparameter_env_version_index", "environment", "version"),
        Index("unknownparameter_resolved_index", "resolved"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    environment: Mapped[uuid.UUID] = mapped_column(UUID)
    source: Mapped[str] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer)
    resource_id: Mapped[Optional[str]] = mapped_column(String, server_default=text("''::character varying"))
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB)
    resolved: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))

    configurationmodel: Mapped["ConfigurationModel"] = relationship("ConfigurationModel", back_populates="unknownparameter")
    environment_: Mapped["Environment"] = relationship("Environment", back_populates="unknownparameter")


class Agent(Base):
    __tablename__ = "agent"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="agent_environment_fkey"),
        ForeignKeyConstraint(["id_primary"], ["agentinstance.id"], ondelete="RESTRICT", name="agent_id_primary_fkey"),
        PrimaryKeyConstraint("environment", "name", name="agent_pkey"),
        Index("agent_id_primary_index", "id_primary"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, primary_key=True)
    last_failover: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    paused: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))
    id_primary: Mapped[Optional[uuid.UUID]] = mapped_column(UUID)
    unpause_on_resume: Mapped[Optional[bool]] = mapped_column(Boolean)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="agent")
    agentinstance: Mapped["AgentInstance"] = relationship("AgentInstance", back_populates="agent")


# Currently, sqlalchemy-strawberry does not support relationship tables.
# There are some discussions to see if we will modify the underlying schema as to not need this table.
# When we create the `Resource` strawberry model we should exclude the relation to `ResourceAction`

t_resourceaction_resource = Table(
    "resourceaction_resource",
    Base.metadata,
    Column("environment", UUID, primary_key=True, nullable=False),
    Column("resource_action_id", UUID, primary_key=True, nullable=False),
    Column("resource_id", String, primary_key=True, nullable=False),
    Column("resource_version", Integer, primary_key=True, nullable=False),
    ForeignKeyConstraint(
        ["environment", "resource_id", "resource_version"],
        ["resource.environment", "resource.resource_id", "resource.model"],
        ondelete="CASCADE",
        name="resourceaction_resource_environment_resource_id_resource_v_fkey",
    ),
    ForeignKeyConstraint(
        ["resource_action_id"],
        ["resourceaction.action_id"],
        ondelete="CASCADE",
        name="resourceaction_resource_resource_action_id_fkey",
    ),
    PrimaryKeyConstraint(
        "environment", "resource_id", "resource_version", "resource_action_id", name="resourceaction_resource_pkey"
    ),
    Index("resourceaction_resource_environment_resource_version_index", "environment", "resource_version"),
    Index("resourceaction_resource_resource_action_id_index", "resource_action_id"),
)
