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
import json

from asyncpg import Connection

DISABLED = False


async def update(connection: Connection) -> None:
    # Replace all log entries with level NOTSET

    # Split into two queries because on query would be very complicated
    # This is not very likely to every be needed

    detection_query = """
    SELECT distinct action_id, messages
    FROM public.resourceaction,
         unnest(messages) arr(msg)
    WHERE msg->'level'='"NOTSET"';
    """

    update_query = """
    UPDATE public.resourceaction
    SET messages = $1
    WHERE action_id = $2
    """

    async with connection.transaction():
        # Get all bad records
        results = await connection.fetch(detection_query)
        for result in results:
            # Decode, filter and update
            aid = result["action_id"]
            messages = result["messages"]
            for i, message in enumerate(messages):
                message_decoded = json.loads(message)
                if message_decoded["level"] == "NOTSET":
                    message_decoded["level"] = "TRACE"
                    messages[i] = json.dumps(message_decoded)
            await connection.execute(update_query, messages, aid)
