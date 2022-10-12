# Data collector design


    In order to train the Predictive Test Selection algorithm, we need a dataset.
    This dataset holds historic information about past test runs:

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
