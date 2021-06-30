"""
    Copyright 2021 Inmanta

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
from typing import Any, Dict, Mapping, MutableMapping, Optional, cast

from inmanta.protocol.common import JSON_CONTENT, ReturnValue, T
from inmanta.types import ArgumentTypes, ReturnTypes


class ReturnValueWithMeta(ReturnValue[T]):
    def __init__(
        self,
        status_code: int = 200,
        headers: MutableMapping[str, str] = {},
        response: Optional[T] = None,
        content_type: str = JSON_CONTENT,
        links: Optional[Dict[str, str]] = None,
        metadata: Optional[Mapping[str, ArgumentTypes]] = None,
    ) -> None:
        super().__init__(status_code, headers, response, content_type, links)
        self.metadata = metadata

    def _get_with_envelope(self, envelope_key: str) -> ReturnTypes:
        """Get the body with an envelope specified"""
        response = cast(Dict[str, Any], super()._get_with_envelope(envelope_key))
        if self.metadata:
            if response.get("metadata"):
                response["metadata"].update(self.metadata)
            else:
                response["metadata"] = self.metadata
        return response

    def _get_without_envelope(self) -> ReturnTypes:
        """Get the body without an envelope specified"""
        response = super()._get_without_envelope()
        if self.metadata:
            if isinstance(response, Dict):
                if response.get("metadata"):
                    response["metadata"].update(self.metadata)
                else:
                    response["metadata"] = self.metadata
        return response
