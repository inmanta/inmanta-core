from setuptools import setup, find_packages

setup(
    name="impera",
    package_dir={"" : "src" },
    packages=find_packages("src"),
    version="0.7a1",
    description="Impera management tool",
    author="Bart Vanbrabant",
    author_email="bart@impera.io",
    license="LICENSE",

    scripts=["bin/impera"],
    package_data={"" : ["misc/*", "docs/*"]},
    include_package_data=True,
)
