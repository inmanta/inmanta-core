# Naming
From iso4 on (>=4.2.0), database schema update files should be named `v<timestamp><i>.py` where the timestamp is in the form
`YYYYMMDD` and `i` is an index to allow more than one schema update per day (e.g. `v202102220.py`).

For iso3 (~=3.0.0), the legacy (incremental) versioning schema should still be used.
