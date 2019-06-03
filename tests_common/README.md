# Pytest-Inmanta-tests

This package contains test code used by the Inmanta core and its extensions. It exposes a set of pytest fixtures as a pytest 
plugin.

## Installation

### 1) Manually

```bash
pip install -U setuptools pip
python3 tests_common/copy_files_from_core.py
pip install tests_common/
```

The `copy_files_from_core.py` script copies the files it requires from `tests/` into `tests_common/src/`. 

### 2) Via makefile

```bash
make install-tests
```
