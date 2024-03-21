import json
import logging

import inmanta.data

basic = inmanta.data.BaseDocument.select_query


def hook_base_document():

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
                logging.getLogger("PERF").warning("PLAN: \n%s \n %s", query, json.dumps(await stmt.explain(*values)))
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
