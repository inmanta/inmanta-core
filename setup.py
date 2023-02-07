from setuptools import setup, find_namespace_packages
from os import path

requires = [
    "asyncpg~=0.25,<0.28",
    "click-plugins~=1.0",
    # click has been known to publish non-backwards compatible minors in the past (removed deprecated code in 8.1.0)
    "click>=8.0,<8.2",
    "colorlog~=6.4",
    "cookiecutter>=1,<3",
    "crontab>=0.23,<2.0",
    "cryptography>=36,<40",
    # docstring-parser has been known to publish non-backwards compatible minors in the past
    "docstring-parser>=0.10,<0.16",
    "email-validator~=1.0",
    "execnet~=1.0",
    "importlib_metadata>=4,<7",
    "jinja2~=3.0",
    "more-itertools>=8,<10",
    "netifaces~=0.11",
    # leave upper bound floating for fast-moving and extremely stable packaging
    "packaging>=21.3",
    # pip>=21.3 required for editable pyproject.toml + setup.cfg based install support
    "pip>=21.3",
    "ply~=3.0",
    # Exclude pre-release due to https://github.com/samuelcolvin/pydantic/issues/3546
    "pydantic~=1.0,!=1.9.0a1",
    "pyformance~=0.4",
    "PyJWT~=2.0",
    "python-dateutil~=2.0",
    "pyyaml~=6.0",
    "texttable~=1.0",
    "tornado~=6.0",
    "typing_inspect~=0.7",
    "build~=0.7",
    "ruamel.yaml~=0.17",
    "toml~=0.10 ",
]


# read the contents of your README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

version = "8.2.0"

setup(
    version=version,
    python_requires=">=3.9",  # also update classifiers
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
        "Programming Language :: Python :: 3.9",
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
        "debug": ["rpdb"],
        # option to install a matched pair of inmanta-core and pytest-inmanta-extensions
        "pytest-inmanta-extensions": [f"pytest-inmanta-extensions~={version}.0.dev"],
        "datatrace": ["graphviz"],
    },
    entry_points={
        "console_scripts": [
            "inmanta-cli = inmanta.main:main",
            "inmanta = inmanta.app:app",
        ],
    },
)
