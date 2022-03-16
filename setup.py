from setuptools import setup, find_packages
from os import path

requires = [
    "asyncpg",
    "click-plugins",
    "click",
    "colorlog",
    "cookiecutter",
    "cryptography",
    # docstring-parser has been known to publish non-backwards compatible minors in the past
    "docstring-parser>=0.10,<0.14.0",
    "email-validator",
    "execnet",
    "importlib_metadata",
    "jinja2",
    "more-itertools",
    "netifaces",
    "packaging",
    "ply",
    # Exclude pre-release due to https://github.com/samuelcolvin/pydantic/issues/3546
    "pydantic!=1.9.0a1",
    "pyformance",
    "PyJWT",
    "python-dateutil",
    "pyyaml",
    "texttable",
    "tornado",
    "typing_inspect",
]

# Package a dummy extensions so that the namespace package for extensions is not empty
namespace_packages = ["inmanta_ext.core"]

# read the contents of your README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

version = "4.4.2"

setup(
    version=version,
    python_requires=">=3.6",  # also update classifiers
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
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    keywords="orchestrator orchestration configurationmanagement",
    project_urls={
        "Bug Tracker": "https://github.com/inmanta/inmanta-core/issues",
        "Documentation": "https://docs.inmanta.com/community/latest/",
    },
    # Packaging
    package_dir={"": "src"},
    packages=find_packages("src") + namespace_packages,
    # https://www.python.org/dev/peps/pep-0561/#packaging-type-information
    package_data={"": ["misc/*", "docs/*"], "inmanta": ["py.typed"]},
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
