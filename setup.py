from setuptools import setup, find_packages

requires = [
        'click',
        'texttable',
        'execnet',
        'tornado',
        'colorlog',
        'urllib3',
        'python-dateutil',
        'ply',
        'pyyaml',
        'ruamel.yaml',
        'virtualenv',
        'motor >= 1.1',
        'pymongo',
        'mongobox']

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
