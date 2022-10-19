# Overview

    This project is based off this [paper](https://arxiv.org/abs/1810.05286)
    The main idea is to get faster feedback when pushing changes to a feature branch by only running a small subset of
    the test suite. To find which tests to run we use a predictive model that takes 2 inputs:

    graph model;
        Code change-->Model;
        Test Case fqn -->Model;
        Model-->Failure proba;

    ## A code change

    This is a set of files that were modified in this pull request

    ## A test case

    This is the fully qualified name of the

# Data collector design


    In order to train the Predictive Test Selection algorithm, we need a dataset. This dataset holds historic
    information about past test runs. It can be consulted [here](https://grafana.inmanta.com/d/YsUw7VSVk/test-failure-rates?orgId=1&from=now%2Fy&to=now)

    Generic information about the influx db data point format can be found [here](https://docs.influxdata.com/influxdb/v1.8/write_protocols/line_protocol_tutorial/)


    """
    x date text NOT NULL,
      test_fqn text NOT NULL,
    x commit_hash text NOT NULL,
    x n_changes_3 int NOT NULL,
    x n_changes_14 int NOT NULL,
    x n_changes_56 int NOT NULL,
    x file_cardinality int NOT NULL,
    x file_extension text NOT NULL,
      target_cardinality int NOT NULL,
      failure_rate_7 real NOT NULL,
      failure_rate_14 real NOT NULL,
      failure_rate_28 real NOT NULL,
      failure_rate_56 real NOT NULL,
      test_failed int NOT NULL
    """

# Predictor design

    Ultimately the predictor outputs a probability of failure for the given inputs (code_change, test_file)
