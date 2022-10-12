import pytest

from collect_test_failure_data import parse_xml_test_results_old


@pytest.mark.parametrize(
    "path",
    [
        "data/out.xml",
        "data/out_2.xml",
        "data/full_test_output.xml",
    ],
)
def test_basic_xml_parsing(path):
    parse_xml_test_results_old(path)
