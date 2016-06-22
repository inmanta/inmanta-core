from setuptools import setup, find_packages

setup(
    name="inmanta",
    package_dir={"" : "src"},
    packages=find_packages("src"),
    version="2016.3",
    description="Inmanta Deployment Platform",
    author="Inmanta",
    author_email="code@inmanta.com",
    license="Apache Software License",

    scripts=["bin/inmanta"],
    package_data={"" : ["misc/*", "docs/*"]},
    include_package_data=True,

    install_requires=['cliff <= 2.0.0'],

    entry_points={
    'console_scripts': [
        'inmanta-cli = inmanta.main:main'
    ],
    'inmanta': [
        'project-list = inmanta.client:ProjectList',
        'project-create = inmanta.client:ProjectCreate',
        'project-delete = inmanta.client:ProjectDelete',
        'project-show = inmanta.client:ProjectShow',
        'project-modify = inmanta.client:ProjectModify',

        'environment-create = inmanta.client:EnvironmentCreate',
        'environment-list = inmanta.client:EnvironmentList',
        'environment-show = inmanta.client:EnvironmentShow',
        'environment-modify = inmanta.client:EnvironmentModify',
        'environment-delete = inmanta.client:EnvironmentDelete',

        'version-list = inmanta.client:VersionList',
        'version-release = inmanta.client:VersionRelease',
        'version-report = inmanta.client:VersionReport',

        'agent-list = inmanta.client:AgentList',

        'param-list = inmanta.client:ParamList',
        'param-set = inmanta.client:ParamSet',
        'param-get = inmanta.client:ParamGet',

        'form-list = inmanta.client:FormList',
        'form-show = inmanta.client:FormShow',
        'form-export = inmanta.client:FormExport',

        'record-list = inmanta.client:RecordList',
        'record-create = inmanta.client:RecordCreate',
        'record-delete = inmanta.client:RecordDelete',
        'record-update = inmanta.client:RecordUpdate',
    ],
},
)
