from inmanta import data
import pytest


async def test_environment_no_environment_name(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()
    with pytest.raises(AttributeError):
        data.Environment(project=project.id, repo_url="", repo_branch="")


async def test_environment_no_project_id(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()
    with pytest.raises(AttributeError):
        data.Environment(name="dev", repo_url="", repo_branch="")
