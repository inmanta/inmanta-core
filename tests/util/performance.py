"""
    Copyright 2023 Inmanta

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

import json
import logging

import inmanta.data

basic = inmanta.data.BaseDocument.select_query


def hook_base_document():
    """A small testing utility to analyze query performance"""

    async def select_query(
        cls,
        query: str,
        values: list[object],
        no_obj: bool = False,
        connection=None,
    ):
        async with cls.get_connection(connection) as con:
            async with con.transaction():
                stmt = await con.prepare(query)
                explain_analyze = json.dumps(await stmt.explain(*values, analyze=True))
                logging.getLogger("PERF").warning("PLAN: \n%s \n %s", query, explain_analyze)
                result = []
                async for record in stmt.cursor(*values):
                    if no_obj:
                        result.append(record)
                    else:
                        result.append(cls(from_postgres=True, **record))
                return result

    inmanta.data.BaseDocument.select_query = classmethod(select_query)


def unhook_base_document():
    inmanta.data.BaseDocument.select_query = basic
