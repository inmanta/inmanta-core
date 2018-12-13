from integration import run_async, Environment
import time


class ApiPerformanceTester(object):

    def get_time_elapse_to_get_resources_in_version(self, environment):
        latest_version = run_async(lambda: environment.get_latest_version())
        duration_in_seconds = self._get_duration(lambda: environment.get_resources_in_version(latest_version))
        return duration_in_seconds

    def get_time_elapse_to_get_resource_logs(self, environment):
        latest_version = run_async(lambda: environment.get_latest_version())
        resources_in_latest_version = run_async(lambda: environment.get_resources_in_version(latest_version))
        resource_id = resources_in_latest_version['resources'][0]['id']
        duration_in_seconds = self._get_duration(lambda: environment.get_resource_logs(resource_id))
        return duration_in_seconds

    def get_time_elapse_to_get_resources_overview(self, environment):
        duration_in_seconds = self._get_duration(lambda: environment.get_resources_overview())
        return duration_in_seconds

    def _get_duration(self, func):
        now = time.time()
        run_async(func)
        then = time.time()
        duration_in_seconds = then - now
        return duration_in_seconds
