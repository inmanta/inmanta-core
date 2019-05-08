from setuptools import setup, find_packages

requires = [
    "asyncpg",
    "click",
    "colorlog",
    "execnet",
    "netifaces",
    "ply",
    "python-dateutil",
    "pyyaml",
    "texttable",
    "tornado",
    "typing",
    "PyJWT",
    "cryptography",
    "jinja2",
    "pyformance",
    "pymongo",
]

setup(
    version="2019.2.1",
    python_requires='>=3.6', # also update classifiers
    # Meta data
    name="inmanta",
    description="Inmanta deployment tool",
    author="Inmanta",
    author_email="code@inmanta.com",
    url="https://github.com/inmanta/inmanta",
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
        "Programming Language :: Python :: 3.7"
    ],
    keywords="orchestrator orchestration configurationmanagement",
    project_urls={
        "Bug Tracker": "https://github.com/inmanta/inmanta/issues",
        "Documentation": "https://docs.inmanta.com/community/latest/",
    },
    # Packaging
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={"": ["misc/*", "docs/*"]},
    include_package_data=True,
    install_requires=requires,
    entry_points={
        "console_scripts": [
            "inmanta-cli = inmanta.main:main",
            "inmanta = inmanta.app:app",
            "inmanta-migrate-db = inmanta.db.migrate_to_postgresql:main",
        ]
    },

)
