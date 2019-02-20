from typing import Optional, Union, Dict, Any, List, Type, Pattern
from tornado import web, httputil, routing


class Matcher:
    ...

class PathMatches(Matcher):
    def __init__(self, path_pattern: Union[str, Pattern]) -> None: ...

class Rule(object):
    def __init__(
        self, matcher: routing.Matcher, target: Type[web.RequestHandler], target_kwargs: Optional[Any] = None
    ) -> None: ...
