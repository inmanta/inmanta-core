from setuptools import setup, find_packages

requires = [
        'click',
        'colorlog',
        'execnet',
        'mongobox',
        'motor >= 1.1',
        'netifaces',
        'ply',
        'pymongo',
        'python-dateutil',
        'pyyaml',
        'texttable',
        'tornado',
        'typing',
        'virtualenv',
        'typing',
        'PyJWT',
        'cryptography'
    ]

setup(
    name="inmanta",
    package_dir={"" : "src"},
    packages=find_packages("src"),
    version="2017.4",
    description="Inmanta deployment tool",
    author="Inmanta",
    author_email="code@inmanta.com",
    license="Apache Software License",

    package_data={"" : ["misc/*", "docs/*"]},
    include_package_data=True,

    install_requires=requires,
    # setup_requires=['tox-setuptools', 'tox'],

    entry_points={
    'console_scripts': [
        'inmanta-cli = inmanta.main:main',
        'inmanta = inmanta.app:app'
    ],
},
)
