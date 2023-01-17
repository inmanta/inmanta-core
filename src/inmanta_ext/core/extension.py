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

from inmanta.server import agentmanager, server
from inmanta.server.extensions import ApplicationContext
from inmanta.server.services import (
    codeservice,
    compilerservice,
    databaseservice,
    dryrunservice,
    environment_metrics_service,
    environmentservice,
    fileservice,
    metricservice,
    notificationservice,
    orchestrationservice,
    paramservice,
    projectservice,
    resourceservice,
)


def setup(application: ApplicationContext) -> None:
    application.register_slice(server.Server())
    application.register_slice(agentmanager.AgentManager())
    application.register_slice(agentmanager.AutostartedAgentManager())
    application.register_slice(databaseservice.DatabaseService())
    application.register_slice(compilerservice.CompilerService())
    application.register_slice(projectservice.ProjectService())
    application.register_slice(environmentservice.EnvironmentService())
    application.register_slice(fileservice.FileService())
    application.register_slice(codeservice.CodeService())
    application.register_slice(metricservice.MetricsService())
    application.register_slice(paramservice.ParameterService())
    application.register_slice(resourceservice.ResourceService())
    application.register_slice(orchestrationservice.OrchestrationService())
    application.register_slice(dryrunservice.DyrunService())
    application.register_slice(notificationservice.NotificationService())
    application.register_slice(environment_metrics_service.EnvironmentMetricsService())
