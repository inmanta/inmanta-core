import unittest
from impera.module import Project
import impera.compiler as compiler
from nose.tools import raises, assert_equal, assert_true


class testModuleTool(unittest.TestCase):
    
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        self.file = "tests/data/compile_test_1"
    def setUp(self):
        Project.set(Project(self.file))
        
    def test_compile(self):
        (types,scopes) = compiler.do_compile()
        instances = types["__config__::Host"].get_all_instances()
        assert_equal(len(instances), 1)
        i = instances[0]
        assert_equal(i.get_attribute("name").get_value(),"test1")
        assert_equal(i.get_attribute("os").get_value().get_attribute("name").get_value(),"linux")