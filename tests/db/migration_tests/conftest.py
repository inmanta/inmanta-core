"""
    Copyright 2024 Inmanta

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

import pytest

from inmanta.server.services import environment_metrics_service, notificationservice, compilerservice


@pytest.fixture
def server_pre_start(server_config):
    """
    This fixture is called before the server starts to disable all background tasks
    """
    old_disable_env_metrics_service = environment_metrics_service.DISABLE_ENV_METRICS_SERVICE
    old_disable_notification_cleanup = notificationservice.DISABLE_NOTIFICATION_CLEANUP
    old_disable_compile_cleanup = compilerservice.DISABLE_COMPILE_CLEANUP
    environment_metrics_service.DISABLE_ENV_METRICS_SERVICE = True
    notificationservice.DISABLE_NOTIFICATION_CLEANUP = True
    compilerservice.DISABLE_COMPILE_CLEANUP = True
    yield
    environment_metrics_service.DISABLE_ENV_METRICS_SERVICE = old_disable_env_metrics_service
    notificationservice.DISABLE_NOTIFICATION_CLEANUP = old_disable_notification_cleanup
    compilerservice.DISABLE_COMPILE_CLEANUP = old_disable_compile_cleanup
