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

import asyncio
import datetime
import json
import uuid

from pyformance import global_registry

from inmanta import const
from inmanta.data import ResourceAction
from inmanta.data.model import AttributeStateChange
from inmanta.util import get_compiler_version


async def test_resource_deploy_performance(server, client, clienthelper, environment, agent, caplog):
    """
    Method to 'quickly' benchmark the deploy performance wrt to the database

    Not run by default, because filename doesn't start with test
    """
    n_version = 5
    n_resources = 200
    n_deploys = 5
    dependency_density = 5

    env_id = uuid.UUID(environment)

    start = datetime.datetime.now()

    for model_version in range(1, n_version + 1):
        version = await clienthelper.get_version()

        resources = [
            {
                "key": f"key{resource}",
                "value": "value1",
                "id": f"test::Resource[agent1,key=key{resource}],v={version}",
                "send_event": False,
                "purged": False,
                "requires": [
                    f"test::Resource[agent1,key=key{dresource}],v={version}"
                    for dresource in range(1, max(1, resource - dependency_density))
                ],
            }
            for resource in range(1, n_resources + 1)
        ]

        result = await client.put_version(
            tid=env_id,
            version=version,
            resources=resources,
            resource_state={},
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )
        assert result.code == 200

        for deploy in range(1, n_deploys + 1):
            # run in parallel a bit

            batches = 10
            per_batch = int(n_resources / batches)

            async def run_batch(index):
                for resource in range((per_batch * index) + 1, (per_batch * (index + 1) + 1)):
                    action_id = uuid.uuid4()
                    rvid = f"test::Resource[agent1,key=key{resource}],v={version}"
                    result = await agent._client.resource_deploy_start(tid=env_id, rvid=rvid, action_id=action_id)
                    assert result.code == 200, result.result

                    result = await agent._client.resource_did_dependency_change(tid=environment, rvid=rvid)
                    assert result.code == 200, result.result

                    result = await agent._client.resource_deploy_done(
                        tid=env_id,
                        rvid=rvid,
                        action_id=action_id,
                        status=const.ResourceState.deployed,
                        messages=[],
                        changes={"attr1": AttributeStateChange(current=None, desired="test")},
                        change=const.Change.created,
                    )
                    assert result.code == 200, result.result

            await asyncio.gather(*[run_batch(i) for i in range(0, batches)])
            end = datetime.datetime.now()
            time = end - start
            start = end
            print(f"Version {model_version}, Deploy {deploy}: {time}")

    print(json.dumps(global_registry().dump_metrics(), indent=4))

    key_query = """
    SELECT DISTINCT ra.* FROM public.resource as r INNER JOIN public.resourceaction_resource as jt
                        ON r.environment = jt.environment
                        AND r.resource_id = jt.resource_id
                        AND r.model = jt.resource_version
                    INNER JOIN public.resourceaction as ra
                        ON ra.action_id = jt.resource_action_id
                        WHERE
                            r.environment=$1 AND
                            ra.environment=$1 AND
                            resource_type=$2 AND
                            agent=$3 AND
                            r.resource_id_value = $4::varchar AND
                            ra.action=$5
                        ORDER BY started DESC, action_id DESC LIMIT $6"""

    resource_type = "test::Resource"
    agent = "agent1"
    resource_id_value = "key1"
    ra_action = "deploy"
    limit = 1000

    async with ResourceAction.get_connection() as con:
        stmt = await con.prepare(key_query)
        print(json.dumps(await stmt.explain(env_id, resource_type, agent, resource_id_value, ra_action, limit, analyze=True)))

    query_2 = """
        SELECT r1.resource_version_id, r1.last_non_deploying_status
        FROM resource AS r1
        WHERE r1.environment=$1
              AND r1.model=$2
              AND (
                  SELECT (r2.attributes->'requires')::jsonb
                  FROM resource AS r2
                  WHERE r2.environment=$1 AND r2.model=$2 AND r2.resource_version_id=$3
              ) ? r1.resource_version_id
    """
    async with ResourceAction.get_connection() as con:
        stmt = await con.prepare(query_2)
        print(json.dumps(await stmt.explain(env_id, 2, "test::Resource[agent1,key=key3],v=1", analyze=True)))


"""
Baseline output iso5-stable
    n_version = 5
    n_resources = 200
    n_deploys = 5


Version 1, Deploy 1: 0:00:17.253237
Version 1, Deploy 2: 0:00:19.073246
Version 1, Deploy 3: 0:00:19.228956
Version 1, Deploy 4: 0:00:18.323736
Version 1, Deploy 5: 0:00:17.832653
Version 2, Deploy 1: 0:00:17.775826
Version 2, Deploy 2: 0:00:17.729044
Version 2, Deploy 3: 0:00:18.036430
Version 2, Deploy 4: 0:00:17.939229
Version 2, Deploy 5: 0:00:17.704935
Version 3, Deploy 1: 0:00:18.045674
Version 3, Deploy 2: 0:00:17.801741
Version 3, Deploy 3: 0:00:18.487242
Version 3, Deploy 4: 0:00:17.968664
Version 3, Deploy 5: 0:00:18.531737
Version 4, Deploy 1: 0:00:18.220178
Version 4, Deploy 2: 0:00:18.562100
Version 4, Deploy 3: 0:00:18.176581
Version 4, Deploy 4: 0:00:18.498701
Version 4, Deploy 5: 0:00:19.016656
Version 5, Deploy 1: 0:00:19.769237
Version 5, Deploy 2: 0:00:19.392680
Version 5, Deploy 3: 0:00:20.185913
Version 5, Deploy 4: 0:00:20.605222
Version 5, Deploy 5: 0:00:19.624016
{
    "rpc.create_project": {
        "avg": 0.001882314682006836,
        "sum": 0.001882314682006836,
        "count": 1.0,
        "max": 0.001882314682006836,
        "min": 0.001882314682006836,
        "std_dev": 0.0,
        "15m_rate": 0.0021556220672944697,
        "5m_rate": 0.0021556220285193295,
        "1m_rate": 0.002155622000822802,
        "mean_rate": 0.0021556219454297487,
        "50_percentile": 0.001882314682006836,
        "75_percentile": 0.001882314682006836,
        "95_percentile": 0.001882314682006836,
        "99_percentile": 0.001882314682006836,
        "999_percentile": 0.001882314682006836
    },
    "rpc.create_environment": {
        "avg": 0.006136417388916016,
        "sum": 0.006136417388916016,
        "count": 1.0,
        "max": 0.006136417388916016,
        "min": 0.006136417388916016,
        "std_dev": 0.0,
        "15m_rate": 0.002155643456982138,
        "5m_rate": 0.002155643441471774,
        "1m_rate": 0.002155643421529878,
        "mean_rate": 0.0021556434004800992,
        "50_percentile": 0.006136417388916016,
        "75_percentile": 0.006136417388916016,
        "95_percentile": 0.006136417388916016,
        "99_percentile": 0.006136417388916016,
        "999_percentile": 0.006136417388916016
    },
    "rpc.heartbeat": {
        "avg": 1.0071551273463841,
        "sum": 456.241272687912,
        "count": 453.0,
        "max": 1.1111304759979248,
        "min": 0.004378795623779297,
        "std_dev": 0.04774442479664582,
        "15m_rate": 0.9765347025213815,
        "5m_rate": 0.9765346949928805,
        "1m_rate": 0.9765346874643797,
        "mean_rate": 0.9765346749168785,
        "50_percentile": 1.009152889251709,
        "75_percentile": 1.0109639167785645,
        "95_percentile": 1.0141252279281616,
        "99_percentile": 1.034619460105896,
        "999_percentile": 1.1111304759979248
    },
    "rpc.heartbeat_reply": {
        "avg": 0.00041234493255615234,
        "sum": 0.0008246898651123047,
        "count": 2.0,
        "max": 0.0004329681396484375,
        "min": 0.0003917217254638672,
        "std_dev": 2.916561916953867e-05,
        "15m_rate": 0.004311547940389195,
        "5m_rate": 0.00431154791379678,
        "1m_rate": 0.004311547776402641,
        "mean_rate": 0.004311547725433849,
        "50_percentile": 0.00041234493255615234,
        "75_percentile": 0.0004329681396484375,
        "95_percentile": 0.0004329681396484375,
        "99_percentile": 0.0004329681396484375,
        "999_percentile": 0.0004329681396484375
    },
    "rpc.get_state": {
        "avg": 0.002659320831298828,
        "sum": 0.005318641662597656,
        "count": 2.0,
        "max": 0.0038614273071289062,
        "min": 0.00145721435546875,
        "std_dev": 0.0017000352815354216,
        "15m_rate": 0.004311552164155296,
        "5m_rate": 0.00431155213534679,
        "1m_rate": 0.004311552102106206,
        "mean_rate": 0.004311552066649584,
        "50_percentile": 0.002659320831298828,
        "75_percentile": 0.0038614273071289062,
        "95_percentile": 0.0038614273071289062,
        "99_percentile": 0.0038614273071289062,
        "999_percentile": 0.0038614273071289062
    },
    "rpc.reserve_version": {
        "avg": 0.0033983707427978514,
        "sum": 0.016991853713989258,
        "count": 5.0,
        "max": 0.007942914962768555,
        "min": 0.002149343490600586,
        "std_dev": 0.002542028972054395,
        "15m_rate": 0.010781037906758864,
        "5m_rate": 0.010781037757116349,
        "1m_rate": 0.010781037568677635,
        "mean_rate": 0.010781037286019575,
        "50_percentile": 0.002306222915649414,
        "75_percentile": 0.005162358283996582,
        "95_percentile": 0.007942914962768555,
        "99_percentile": 0.007942914962768555,
        "999_percentile": 0.007942914962768555
    },
    "rpc.put_version": {
        "avg": 0.16868414878845214,
        "sum": 0.8434207439422607,
        "count": 5.0,
        "max": 0.18580198287963867,
        "min": 0.1631946563720703,
        "std_dev": 0.009646953055957695,
        "15m_rate": 0.01078365456998846,
        "5m_rate": 0.01078365449790338,
        "1m_rate": 0.010783654398093274,
        "mean_rate": 0.010783654270558139,
        "50_percentile": 0.1652238368988037,
        "75_percentile": 0.1758873462677002,
        "95_percentile": 0.18580198287963867,
        "99_percentile": 0.18580198287963867,
        "999_percentile": 0.18580198287963867
    },
    "rpc.resource_deploy_start": {
        "avg": 0.021790083503723145,
        "sum": 108.95041751861572,
        "count": 5000.0,
        "max": 0.0865776538848877,
        "min": 0.00543975830078125,
        "std_dev": 0.0075171715130414925,
        "15m_rate": 10.788354629563987,
        "5m_rate": 10.788354546316377,
        "1m_rate": 10.788354446419246,
        "mean_rate": 10.788354302123395,
        "50_percentile": 0.023555278778076172,
        "75_percentile": 0.026827991008758545,
        "95_percentile": 0.03353232145309448,
        "99_percentile": 0.0570297288894655,
        "999_percentile": 0.08397920513153077
    },
    "rpc.resource_did_dependency_change": {
        "avg": 0.5393619068622589,
        "sum": 2696.8095343112946,
        "count": 5000.0,
        "max": 1.8580374717712402,
        "min": 0.012372016906738281,
        "std_dev": 0.3144769638592534,
        "15m_rate": 10.789688632114261,
        "5m_rate": 10.789688515538783,
        "1m_rate": 10.789688415616947,
        "mean_rate": 10.789688287939047,
        "50_percentile": 0.5299985408782959,
        "75_percentile": 0.7665501832962036,
        "95_percentile": 1.2162763237953185,
        "99_percentile": 1.4830184030532847,
        "999_percentile": 1.8528694918155677
    },
    "rpc.resource_deploy_done": {
        "avg": 0.025031384468078614,
        "sum": 125.15692234039307,
        "count": 5000.0,
        "max": 0.10410952568054199,
        "min": 0.005109310150146484,
        "std_dev": 0.008782602139116424,
        "15m_rate": 10.79229940532426,
        "5m_rate": 10.79229931646186,
        "1m_rate": 10.792299227599461,
        "mean_rate": 10.792299077644165,
        "50_percentile": 0.0273435115814209,
        "75_percentile": 0.03234308958053589,
        "95_percentile": 0.040170705318450926,
        "99_percentile": 0.059304990768432625,
        "999_percentile": 0.10398823094367983
    },
    "db.connected": {
        "value": true
    },
    "db.max_pool": {
        "value": 10
    },
    "db.open_connections": {
        "value": 10
    },
    "db.free_connections": {
        "value": 10
    },
    "self.spec.cpu": {
        "value": 113799
    }
}
"""
