import os

from moduletool.common import install_project
from inmanta.moduletool import ModuleTool, ProjectTool
from inmanta.module import Project
import subprocess


def test_module_list_underscore_bug(modules_dir: str, modules_repo: str, tmpdir, capsys):
    """
    Verify the fix for the bug where the `inmanta modules list` command incorrectly reports
    that versions match while they don't. This issue was caused by an incorrect comparison
    of the modules names, where one side of the comparison contained underscores and the other
    side contained dashes.
    """
    coroot = install_project(modules_dir, "project_with_underscored_dep_name", tmpdir)

    os.chdir(coroot)
    ModuleTool().execute("install", [])

    def mod_a_version_matches_expected_version(output: str) -> bool:
        lines_about_mod_a = [line for line in output.split("\n") if "mod_a" in line]
        assert len(lines_about_mod_a) == 1
        return lines_about_mod_a[0].split("|")[-2].strip() == "1"

    ModuleTool().execute("list", [])
    # Version 3.2 of mod_a was checked out by the `inmanta module install` command, so the versions match
    assert mod_a_version_matches_expected_version(output=capsys.readouterr().out)

    # Install a version that is incompatible
    subprocess.check_call(["git", "checkout", "4.0.0"], cwd=os.path.join(coroot, "libs", "mod_a"))
    # Reset modules cache
    Project._project = None
    ModuleTool().execute("list", [])
    assert not mod_a_version_matches_expected_version(output=capsys.readouterr().out)
