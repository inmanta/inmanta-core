from _io import StringIO
import os
import logging
import unittest
from unittest import mock

from impera import module
from nose.tools import raises

def test_LocalRepoSuccess():
    