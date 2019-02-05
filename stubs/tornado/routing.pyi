from typing import Optional, Union, Dict, Any, List
from tornado import web, httputil, routing


class Matcher:
    ...

class Rule(object):
    def __init__(self, matcher: routing.Matcher, target: web.RequestHandler, target_kwargs: Any) -> None: ...
