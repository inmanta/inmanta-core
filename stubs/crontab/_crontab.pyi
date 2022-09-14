import datetime

class CronTab:
    def __init__(self, crontab: str, loop: bool = ..., random_seconds: bool = ...) -> None:
        """
        inputs:
            `crontab` - crontab specification of "[S=0] Mi H D Mo DOW [Y=*]"
            `loop` - do we loop when we validate / construct counts
                     (turning 55-5,1 -> 0,1,2,3,4,5,55,56,57,58,59 in a "minutes" column)
            `random_seconds` - randomly select starting second for tasks
        """
        ...

    def next(self, now: datetime.datetime | int | float = ..., *, default_utc: bool = ...,) -> float:
        """
        Returns the number of seconds until the next occurence.

        :param now: The reference time to use. Can be either timezone aware or not but either way no conversion takes place:
            only the time part is taken into account.
        :param default_utc: Ignored if `now` is supplied. If True, uses UTC time as reference.
        """
        ...
