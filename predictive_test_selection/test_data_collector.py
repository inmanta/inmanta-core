import pytest

from collect_data import parse_xml_test_results

@pytest.mark.parametrize("path", [
"data/out.xml",
"data/out_2.xml",
"data/full_test_output.xml",
])
def test_basic_xml_parsing(path):
    parse_xml_test_results(path)
