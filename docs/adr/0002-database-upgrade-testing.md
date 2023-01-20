# Database Upgrade Testing

* Status: accepted
* Deciders: [Sander, Arnaud, Wouter]
* Date: 2023-01-12

## Context and Problem Statement

When making updates to the database schema, it is important to test this. In case the migration includes any data
transformation, testing this commonly involves setting up some known preconditions, and verifying that they are
converted as expected when the migration script is executed. These preconditions should be set up in a way that
remains both valid and relevant for the test scenario, even when related code may change in the future.

How do we set up these preconditions so that the tests remain valid and relevant in the future?

## Decision Drivers

* We want to test that database update code correctly transforms data produced by older code to data that can be handled by the current code
* But within the code base, this older code no longer exists or has been modified, so it can not be relied upon in the test case before the migration, where database schema and code might be out of sync.

## Considered Options

1. Write data corresponding to the old database schema directly in the testcase to the DB.
2. Generate test data using old code and persist it.
3. Dynamically check out old code to run the test

## Decision Outcome

We chose option 1 and 2.

1. When data is very simple or specific, write data to the database in the testcase, prior to the update. Make sure not to use any inmanta code.
2. When the write path is non trivial, use the procedure below:
 - creating test data using the old code,
 - dumping it to file and
 - running it through the update script.
 - afterwards, we test if it still works with the latest code version

In practice, this means that if you write a database update test:
1. update the [dump_tool.py](../../tests/db/migration_tests/dump_tool.py) to produce all data required for your test
2. write a testcase that uses the api to read the data and verify it is as expected
3. commit all changes, except for the dump tool
4. check out master (the dump tool changes remain, as they are not committed)
5. run the dump tool to produce a dump using the old code
6. check out your branch again, commit the dump and `dump_tool`


### Positive Consequences

* We use the actual old code to generate test data
* Technically unsophisticated

### Negative Consequences

* Easy to do wrong. It is more natural to set up the initial state in the testcase itself, as we do everywhere else.
* We accumulate some additional test data in the repo

## Pros and Cons of the Options

### option 1: write data corresponding to the old database schema directly in the testcase to the DB.

* Bad, because it tends to break when the database schema evolves even further
* Bad, because we don't test against the actual older code, but against what we assume it produces

### option 3: Dynamic checkout

* Good, because we test against the actual older code
* Bad, because it is very difficult to do
* Bad, because it is very slow
