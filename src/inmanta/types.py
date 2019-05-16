"""
    Copyright 2019 Inmanta

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: code@inmanta.com
"""
# This file defines named type definition for the Inmanta code base
from typing import Any, Tuple, Dict, Union, Optional, TYPE_CHECKING, Callable, Coroutine

if TYPE_CHECKING:
    # Include imports from other modules here and use the quoted annotation in the definition to prevent import loops
    from inmanta.data.model import BaseModel  # noqa: F401
    from inmanta.protocol.common import ReturnValue  # noqa: F401

JsonType = Dict[str, Any]
ReturnTupple = Tuple[int, Optional[JsonType]]
Apireturn = Union[int, ReturnTupple, "ReturnValue", "BaseModel"]

HandlerType = Callable[..., Coroutine[Any, Any, Apireturn]]
