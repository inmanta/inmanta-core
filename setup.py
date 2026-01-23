from setuptools import setup, find_namespace_packages
from os import path

requires = [
    "asyncpg~=0.25",
    "build~=1.0",
    "click-plugins~=1.0",
    # click has been known to publish non-backwards compatible minors in the past (removed deprecated code in 8.1.0)
    "click>=8.0,<8.4",
    "colorlog~=6.4",
    "cookiecutter>=1,<3",
    "crontab>=0.23,<2.0",
    "cryptography>=36,<47",
    # docstring-parser has been known to publish non-backwards compatible minors in the past
    "docstring-parser>=0.10,<0.18",
    "email-validator>=1,<3",
    "jinja2~=3.0",
    "more-itertools>=8,<11",
    # upper bound on packaging because we use a non-public API that might change in any (non-SemVer) version
    "packaging>=21.3,<26.1",
    # pip>=21.3 required for editable pyproject.toml + setup.cfg based install support
    "pip>=21.3",
    "ply~=3.0",
    "pydantic~=2.5,!=2.9.2",
    "PyJWT~=2.0",
    "pynacl~=1.5",
    "python-dateutil~=2.0",
    "pyyaml~=6.0",
    "setuptools",
    "texttable~=1.0",
    # tornado>6.5 because of CVE https://github.com/advisories/GHSA-7cx3-6m66-7c5m
    "tornado>6.5",
    # lower bound because of ilevkivskyi/typing_inspect#100
    "typing_inspect~=0.9",
    "ruamel.yaml~=0.17",
    "toml~=0.10 ",
    "setproctitle~=1.3",
    "SQLAlchemy~=2.0",
    "strawberry-sqlalchemy-mapper==0.8.0",
    "jsonpath-ng~=1.7",
]


# read the contents of your README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# This version is managed by bumpversion. Should you ever update it manually, make sure to consistently update it everywhere
# (See the bumpversion.cfg file for relevant locations).
version = "18.0.0"

setup(
    version=version,
    python_requires=">=3.12",  # also update classifiers
    # Meta data
    name="inmanta-core",
    description="Inmanta deployment tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Inmanta",
    author_email="code@inmanta.com",
    url="https://github.com/inmanta/inmanta-core",
    license="Apache Software License 2",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Telecommunications Industry",
        "Operating System :: POSIX :: Linux",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="orchestrator orchestration configurationmanagement",
    project_urls={
        "Bug Tracker": "https://github.com/inmanta/inmanta-core/issues",
        "Documentation": "https://docs.inmanta.com/community/latest/",
    },
    # Packaging
    package_dir={"": "src"},
    # All data files should be treated as namespace package according to
    # https://setuptools.pypa.io/en/latest/userguide/datafiles.html#subdirectory-for-data-files
    packages=find_namespace_packages(where="src"),
    # https://www.python.org/dev/peps/pep-0561/#packaging-type-information
    zip_safe=False,
    include_package_data=True,
    install_requires=requires,
    extras_require={
        "dev": [
            # all extra's (for testing and mypy)
            "inmanta-core[datatrace,debug,tracing]",
            # test dependencies
            "inmanta-dev-dependencies[pytest,async,core]",
            "inmanta-module-std",
            "bumpversion",
            "openapi_spec_validator",
            "pep8-naming",
            "pip2pi",
            "psutil",
            "time-machine",
            # types
            "types-python-dateutil",
            "types-PyYAML",
            "types-setuptools",
            "types-toml",
            # doc dependencies
            "furo",
            "inmanta-sphinx",
            "myst-parser",
            "sphinx",
            "sphinx-argparse",
            "sphinx-autodoc-annotation",
            "sphinx-click",
            "sphinxcontrib-contentui",
            "sphinxcontrib.datatemplates",
            "sphinxcontrib-redoc",
            "sphinxcontrib-serializinghtml",
            "sphinx-design",
            "Sphinx-Substitution-Extensions",
        ],
        "debug": ["rpdb"],
        # option to install a matched pair of inmanta-core and pytest-inmanta-extensions
        "pytest-inmanta-extensions": [f"pytest-inmanta-extensions~={version}.0.dev"],
        "datatrace": ["graphviz"],
        "tracing": ["logfire>=0.46,<5.0", "opentelemetry-instrumentation-asyncpg~=0.46b0"],
    },
    entry_points={
        "console_scripts": [
            "inmanta-cli = inmanta.main:main",
            "inmanta = inmanta.app:app",
            "inmanta-initial-user-setup = inmanta.user_setup:main",
        ],
        "inmanta.mypy.methods": [
            "methods_v2 = inmanta.protocol.methods_v2",
            "methods = inmanta.protocol.methods",
        ]
    },
)
