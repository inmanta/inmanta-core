from typing import Optional, Union, Dict, Any, ByteString, List
from tornado import  httputil
import collections

class HTTPHeaders(Dict):
    ...

class HTTPServerRequest:
    body: str
    query_arguments: Dict[str, List[bytes]]
    headers: httputil.HTTPHeaders
    remote_ip: str
