# module_v2_with_version_constraints Module

## Running tests

1. Setup a virtual env 

```bash
mkvirtualenv inmanta-test -p python3
pip install -r requirements.dev.txt
pip install -r requirements.txt

mkdir /tmp/env
export INMANTA_TEST_ENV=/tmp/env
export INMANTA_MODULE_REPO=git@github.com:inmanta/
```

2. Run tests

```bash
pytest tests
```
