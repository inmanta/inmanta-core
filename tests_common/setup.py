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
from os import path

from setuptools import find_namespace_packages, setup

version = "8.2.0"

requires = [
    "asyncpg",
    "click",
    f"inmanta-core~={version}.dev",
    "pip2pi",
    "pyformance",
    "pytest-asyncio",
    "pytest-env",
    "pytest-postgresql>=4",
    "psycopg>=3",
    "tornado",
]

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    version=version,
    python_requires=">=3.6",  # also update classifiers
    # Meta data
    name="pytest-inmanta-extensions",
    description="Inmanta tests package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Inmanta",
    author_email="code@inmanta.com",
    url="https://github.com/inmanta/inmanta",
    license="Apache Software License 2",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Software Development",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Framework :: Pytest",
    ],
    keywords="pytest inmanta tests",
    project_urls={"Bug Tracker": "https://github.com/inmanta/inmanta-core/issues"},
    # Packaging
    package_dir={"": "src"},
    # All data files should be treated as namespace package according to
    # https://setuptools.pypa.io/en/latest/userguide/datafiles.html#subdirectory-for-data-files
    packages=find_namespace_packages(where="src"),
    include_package_data=True,
    install_requires=requires,
    entry_points={"pytest11": ["pytest-inmanta-tests = inmanta_tests.plugin"]},
)
