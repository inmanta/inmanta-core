import gc
import sys


def total_size():
    return sum(sys.getsizeof(x) for x in gc.get_objects())
