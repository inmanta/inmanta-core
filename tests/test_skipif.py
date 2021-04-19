from utils import mark_only_for_version_higher_then


@mark_only_for_version_higher_then("10000000000.0.0")
def test_it():
    assert False, "Should be skipped"
