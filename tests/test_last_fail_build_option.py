import datetime
import logging

logger = logging.getLogger(__name__)


def test_always_fail():
    logger.info(test_always_fail)
    raise Exception("Test can't succeed")


def test_fail_early():
    now = datetime.datetime.now()
    logger.info(f"test_fail_early {now.second=}")
    if now.second <= 30:
        raise Exception("seconds in [0:30]")




def test_fail_late():
    now = datetime.datetime.now()
    logger.info(f"test_fail_late {now.second=}")
    if now.second > 30:
        raise Exception("seconds in ]30:60]")
