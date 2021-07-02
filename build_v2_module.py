import shutil
import subprocess
import sys
import tempfile
import os
import configparser

if len(sys.argv) < 2:
    raise Exception("Missing argument: <module-path>")

module_path = sys.argv[1]

# Ensure previously created dist dir is removed
dist_dir = os.path.join(module_path, "dist")
if os.path.exists(dist_dir):
    raise Exception("Dist directory is not empty.")

with tempfile.TemporaryDirectory() as tmpdir:
    # Copy module files to tmp dir
    module_copy = os.path.join(tmpdir, "module")
    shutil.copytree(module_path, module_copy)

    # Parse setup.cfg file
    setup_cfg = os.path.join(module_copy, "setup.cfg")
    if not os.path.exists(setup_cfg):
        raise Exception("setup.cfg file doesn't exist")
    config_parser = configparser.ConfigParser()
    config_parser.read(setup_cfg)

    # Obtain module name from setup.cfg
    pkg_name = config_parser.get("metadata", "name")
    if pkg_name is None:
        raise Exception("Name property not set in setup.cfg")
    module_name = pkg_name[len("inmanta-module-"):]

    # Add options to setup.cfg required for build
    if not config_parser.has_section("options"):
        config_parser.add_section("options")
    config_parser.set("options", "zip_safe", "False")
    config_parser.set("options", "include_package_data", "True")
    config_parser.set("options", "packages", f"inmanta_plugins.{module_name}")
    if not config_parser.has_section("options.package_data"):
        config_parser.add_section("options.package_data")
    # TODO: All subdirectories should be added to this option as well, otherwise they don't get packaged
    config_parser.set("options.package_data", f"inmanta_plugins.{module_name}", "files/*, model/*, templates/*, setup.cfg")

    # Constrain compiler_version in install_requires when specified in setup.cfg
    if config_parser.has_option("metadata", "compiler_version"):
        compiler_version = config_parser.get("metadata", "compiler_version")
        install_requires = config_parser.get("options", "install_requires", fallback="")
        if int(compiler_version.split(".")[0]) < 2016:
            install_requires += f"\ninmanta-core>={compiler_version}"
            config_parser.set("options", "install_requires", install_requires)
        else:
            print("Ignoring the compiler_version, because it relies on the previous interpretation of the field, "
                  "which was coupled to the Inmanta OSS product version instead of the inmanta-core version.")

    # Write out updated setup.cfg file
    with open(setup_cfg, "w") as fd:
        config_parser.write(fd)

    # Copy model, files and templates directories into python package together with the metadatafile of the module (setup.cfg)
    python_pkg_dir = os.path.join(module_copy, "inmanta_plugins", module_name)
    for dir_name in ["model", "files", "templates"]:
        fq_dir_name = os.path.join(module_copy, dir_name)
        if os.path.exists(fq_dir_name):
            shutil.move(fq_dir_name, python_pkg_dir)
    metadata_file = os.path.join(module_copy, "setup.cfg")
    shutil.copy(metadata_file, python_pkg_dir)

    # Create venv for build
    venv_dir = os.path.join(tmpdir, "venv")
    subprocess.call(["python3.6", "-m", "venv", venv_dir])
    subprocess.call([f"{venv_dir}/bin/pip", "install", "-U", "pip"])
    subprocess.call([f"{venv_dir}/bin/pip", "install", "build"])
    subprocess.call([f"{venv_dir}/bin/python", "-m", "build", "--wheel"], cwd=module_copy)

    # Copy dist dir from tmp directory to directory original module
    module_copy_dist_dir = os.path.join(module_copy, "dist")
    shutil.copytree(module_copy_dist_dir, dist_dir)

