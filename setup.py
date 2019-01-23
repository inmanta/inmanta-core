from setuptools import setup, find_packages

requires = [
        'click',
        'colorlog',
        'execnet',
        'motor >= 1.1',
        'netifaces',
        'ply',
        'pymongo',
        'python-dateutil',
        'pyyaml',
        'texttable',
        'tornado < 5',
        'typing',
        'virtualenv<16.1.0',
        'typing',
        'PyJWT',
        'cryptography'
    ]

setup(
    name="inmanta",
    package_dir={"" : "src"},
    packages=find_packages("src"),
    version="2018.3.1",
    description="Inmanta deployment tool",
    author="Inmanta",
    author_email="code@inmanta.com",
    license="Apache Software License 2",

    package_data={"" : ["misc/*", "docs/*"]},
    include_package_data=True,

    install_requires=requires,

    entry_points={
    'console_scripts': [
        'inmanta-cli = inmanta.main:main',
        'inmanta = inmanta.app:app'
    ],
},
)
