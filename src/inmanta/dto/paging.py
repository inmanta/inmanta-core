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

from typing import Optional

from inmanta.types import PRIMITIVE_SQL_TYPES


class PagingBoundaries:
    """
    Represents the lower and upper bounds that should be used for the next and previous pages
    when listing domain entities.

    The largest / smallest value of the current page represents respectively the min / max boundary value (exclusive) for the
    neighbouring pages. Which represents next and which prev depends on sorting order (ASC or DESC).
    So, while the names "start" and "end" might seem to indicate "left" and "right" of the page, they actually mean "highest"
    and "lowest".

    Let's show this in an example: a user requests the following:
     - all Resources with name > foo
     - ASCENDING order
     - Page size = 10

    The equivalent RequestPagingBoundary will be as follows:
        ```
        RequestPagingBoundary:
            start = foo
            end = None
        ```

    The fetched data will be: [foo1 ... foo10]

    But the Pagingboundary will be constructed this way:
        ```
        Pagingboundary:
            end = foo1
            start = foo10 # Reversed because these are meant to map to like-named fields on neighbouring RequestedPagingBoundary
        ```

    :param start: largest value of current page for the primary sort column.
    :param end: smallest value of current page for the primary sort column.
    :param first_id: largest value of current page for the secondary sort column, if there is one.
    :param last_id: smallest value of current page for the secondary sort column, if there is one.
    """

    def __init__(
        self,
        start: Optional[PRIMITIVE_SQL_TYPES],  # Can be none if user selected field is nullable
        end: Optional[PRIMITIVE_SQL_TYPES],  # Can be none if user selected field is nullable
        first_id: Optional[PRIMITIVE_SQL_TYPES],  # Can be none if single keyed
        last_id: Optional[PRIMITIVE_SQL_TYPES],  # Can be none if single keyed
    ) -> None:
        self.start = start
        self.end = end
        self.first_id = first_id
        self.last_id = last_id
