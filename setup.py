from setuptools import setup, find_packages

setup(
    name="impera",
    package_dir={"" : "src" },
    packages=find_packages("src"),
    version="0.1",
    description="Impera management tool",
    author="Bart Vanbrabant",
    author_email="bart.vanbrabant@cs.kuleuven.be",
    license="LICENSE",

    scripts=["bin/impera"],
    package_data={"" : ["misc/*"]},
    include_package_data=True,
)
