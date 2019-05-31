from setuptools import setup, find_packages

requires = [
    "asyncpg",
    "pyformance",
    "tornado",
    "click",
    "typing",
    "pytest-postgresql",
    "pytest-asyncio",
    "pytest-env",
]

setup(
    version="2019.3",
    python_requires=">=3.6",  # also update classifiers
    # Meta data
    name="pytest-inmanta-tests",
    description="Inmanta tests package",
    long_description="This package contains test code which is used by the Inmanta core and its extensions",
    long_description_content_type='text/markdown',
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
    project_urls={
        "Bug Tracker": "https://github.com/inmanta/inmanta/issues"
    },
    # Packaging
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    install_requires=requires,
    entry_points={"pytest11": ["pytest-inmanta-tests = inmanta_tests.plugin"]},
)
