from setuptools import setup, find_packages

requires = [
        'click',
        'colorlog',
        'execnet',
        'mongobox',
        'motor >= 1.1',
        'ply',
        'pymongo',
        'python-dateutil',
        'pyyaml',
        'ruamel.yaml',
        'texttable',
        'tornado',
        'typing',
        'virtualenv',
    ]

setup(
    name="inmanta",
    package_dir={"" : "src"},
    packages=find_packages("src"),
    version="2017.2",
    description="Inmanta deployment tool",
    author="Inmanta",
    author_email="code@inmanta.com",
    license="Apache Software License",

    scripts=["bin/inmanta"],
    package_data={"" : ["misc/*", "docs/*"]},
    include_package_data=True,

    install_requires=requires,
    # setup_requires=['tox-setuptools', 'tox'],

    entry_points={
    'console_scripts': [
        'inmanta-cli = inmanta.main:main'
    ],
},
)
