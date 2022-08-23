"""
    Copyright 2022 Inmanta

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
import os
from collections import abc

import pytest


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202206290.sql"))
async def test_added_resource_join_table(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    postgresql_client,
) -> None:
    """
    Test the database migration script that adds the `resource_set` column to the database.

    """
    all_ras = await postgresql_client.fetch(
        """SELECT ra.action_id, r.environment, r.resource_version_id FROM public.resourceaction as ra
                INNER JOIN public.resource as r
                ON r.resource_version_id = ANY(ra.resource_version_ids)
                AND r.environment = ra.environment
        """
    )
    all_ra_set = {(r[0], r[1], r[2]) for r in all_ras}
    assert len(all_ra_set) != 0

    # Migrate DB schema
    await migrate_db_from()

    post_ra_one = await postgresql_client.fetch(
        """SELECT ra.action_id, r.environment, r.resource_version_id FROM public.resourceaction as ra
                INNER JOIN public.resource as r
                ON r.resource_version_id = ANY(ra.resource_version_ids)
                AND r.environment = ra.environment
        """
    )
    assert all_ra_set == {(r[0], r[1], r[2]) for r in post_ra_one}

    post_ra_two = await postgresql_client.fetch(
        """SELECT ra.action_id, r.environment, r.resource_version_id FROM public.resource as r
                INNER JOIN public.resourceaction_resource as jt
                    ON r.environment = jt.environment
                    AND r.resource_id = jt.resource_id
                    AND r.model = jt.resource_version
                INNER JOIN public.resourceaction as ra
                    ON ra.action_id = jt.resource_action_id
        """
    )
    assert all_ra_set == {(r[0], r[1], r[2]) for r in post_ra_two}
