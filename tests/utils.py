from tornado import gen
import time
from tornado.gen import sleep


@gen.coroutine
def retry_limited(fun, timeout):
    start = time.time()
    while time.time() - start < timeout and not fun():
        yield sleep(0.1)
