from typing import Optional, Union, Dict, Any, ByteString, List
from tornado import  httputil
import collections

class HTTPHeaders(Dict):
    ...

class HTTPServerRequest:
    body: Union[str, bytes]
    query_arguments: Dict[str, List[bytes]]
    headers: httputil.HTTPHeaders
