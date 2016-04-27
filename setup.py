from setuptools import setup, find_packages

setup(
    name="impera",
    package_dir={"" : "src" },
    packages=find_packages("src"),
    version="2016.2",
    description="Impera management tool",
    author="Inmanta NV",
    author_email="code@inmanta.com",
    license="Apache Software License",

    scripts=["bin/impera"],
    package_data={"" : ["misc/*", "docs/*"]},
    include_package_data=True,

    install_requires=['cliff'],

    entry_points={
    'console_scripts': [
        'impera-cli = impera.main:main'
    ],
    'impera': [
        'project-list = impera.client:ProjectList',
        'project-create = impera.client:ProjectCreate',
        'project-delete = impera.client:ProjectDelete',
        'project-show = impera.client:ProjectShow',
        'project-modify = impera.client:ProjectModify',

        'environment-create = impera.client:EnvironmentCreate',
        'environment-list = impera.client:EnvironmentList',
        'environment-show = impera.client:EnvironmentShow',
        'environment-modify = impera.client:EnvironmentModify',
        'environment-delete = impera.client:EnvironmentDelete',

        'version-list = impera.client:VersionList',
        'version-release = impera.client:VersionRelease',
        'version-report = impera.client:VersionReport',

        'agent-list = impera.client:AgentList',

        'param-list = impera.client:ParamList',
        'param-set = impera.client:ParamSet',
        'param-get = impera.client:ParamGet',

        'form-list = impera.client:FormList',
        'form-show = impera.client:FormShow',

        'record-list = impera.client:RecordList',
        'record-show = impera.client:RecordShow',
        'record-create = impera.client:RecordCreate',
        'record-delete = impera.client:RecordDelete',
        'record-update = impera.client:RecordUpdate',
    ],
},
)
