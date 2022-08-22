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
    n_resources = 1000
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
                        AND r.resource_version_id = jt.resource_version_id
                    INNER JOIN public.resourceaction as ra
                        ON ra.action_id = jt.resource_action_id
                        WHERE r.environment=$1 AND ra.environment=$1 AND resource_type=$2 AND agent=$3 AND r.resource_id_value = $4::varchar AND ra.action=$5 ORDER BY started DESC, action_id DESC LIMIT $6"""

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
Baseline output
    n_version = 5
    n_resources = 1000
    n_deploys = 5


Version 1, Deploy 1: 0:00:35.797357
Version 1, Deploy 2: 0:00:59.519614
Version 1, Deploy 3: 0:00:15.870217
Version 1, Deploy 4: 0:00:15.929685
Version 1, Deploy 5: 0:00:16.059511
Version 2, Deploy 1: 0:00:16.568770
Version 2, Deploy 2: 0:00:16.433959
Version 2, Deploy 3: 0:00:16.565516
Version 2, Deploy 4: 0:00:16.688652
Version 2, Deploy 5: 0:00:16.779639
Version 3, Deploy 1: 0:00:17.169906
Version 3, Deploy 2: 0:00:17.054186
Version 3, Deploy 3: 0:00:17.268796
Version 3, Deploy 4: 0:00:17.279419
Version 3, Deploy 5: 0:00:17.432677
Version 4, Deploy 1: 0:00:17.649681
Version 4, Deploy 2: 0:00:17.891368
Version 4, Deploy 3: 0:00:18.109088
Version 4, Deploy 4: 0:00:18.345958
Version 4, Deploy 5: 0:00:19.648016
Version 5, Deploy 1: 0:00:20.447883
Version 5, Deploy 2: 0:00:21.587692
Version 5, Deploy 3: 0:00:21.994172
Version 5, Deploy 4: 0:00:19.794013
Version 5, Deploy 5: 0:00:19.878399
{
    "rpc.create_project": {
        "avg": 0.0018091201782226562,
        "sum": 0.0018091201782226562,
        "count": 1.0,
        "max": 0.0018091201782226562,
        "min": 0.0018091201782226562,
        "std_dev": 0.0,
        "15m_rate": 0.0019689466987136695,
        "5m_rate": 0.0019689466774550114,
        "1m_rate": 0.0019689466552720645,
        "mean_rate": 0.001968946585950358,
        "50_percentile": 0.0018091201782226562,
        "75_percentile": 0.0018091201782226562,
        "95_percentile": 0.0018091201782226562,
        "99_percentile": 0.0018091201782226562,
        "999_percentile": 0.0018091201782226562
    },
    "rpc.create_environment": {
        "avg": 0.006681919097900391,
        "sum": 0.006681919097900391,
        "count": 1.0,
        "max": 0.006681919097900391,
        "min": 0.006681919097900391,
        "std_dev": 0.0,
        "15m_rate": 0.0019689646661410114,
        "5m_rate": 0.001968964653200723,
        "1m_rate": 0.0019689646384118214,
        "mean_rate": 0.0019689646180770823,
        "50_percentile": 0.006681919097900391,
        "75_percentile": 0.006681919097900391,
        "95_percentile": 0.006681919097900391,
        "99_percentile": 0.006681919097900391,
        "999_percentile": 0.006681919097900391
    },
    "rpc.heartbeat": {
        "avg": 1.0121714825532875,
        "sum": 495.96402645111084,
        "count": 490.0,
        "max": 1.070859670639038,
        "min": 0.0048482418060302734,
        "std_dev": 0.04591299312842561,
        "15m_rate": 0.9648213582831068,
        "5m_rate": 0.9648213510361143,
        "1m_rate": 0.9648213442420589,
        "mean_rate": 0.9648213320127594,
        "50_percentile": 1.0145505666732788,
        "75_percentile": 1.0164615511894226,
        "95_percentile": 1.0206902384757996,
        "99_percentile": 1.029777452945709,
        "999_percentile": 1.070859670639038
    },
    "rpc.get_state": {
        "avg": 0.0033272504806518555,
        "sum": 0.006654500961303711,
        "count": 2.0,
        "max": 0.005026340484619141,
        "min": 0.0016281604766845703,
        "std_dev": 0.0024028761273030903,
        "15m_rate": 0.003938161664845886,
        "5m_rate": 0.003938161640811085,
        "1m_rate": 0.0039381616075321296,
        "mean_rate": 0.003938161563160191,
        "50_percentile": 0.0033272504806518555,
        "75_percentile": 0.005026340484619141,
        "95_percentile": 0.005026340484619141,
        "99_percentile": 0.005026340484619141,
        "999_percentile": 0.005026340484619141
    },
    "rpc.heartbeat_reply": {
        "avg": 0.00041961669921875,
        "sum": 0.0008392333984375,
        "count": 2.0,
        "max": 0.0004527568817138672,
        "min": 0.0003864765167236328,
        "std_dev": 4.686729554411416e-05,
        "15m_rate": 0.003938170820277562,
        "5m_rate": 0.003938170798091489,
        "1m_rate": 0.003938170768510059,
        "mean_rate": 0.003938170733382111,
        "50_percentile": 0.00041961669921875,
        "75_percentile": 0.0004527568817138672,
        "95_percentile": 0.0004527568817138672,
        "99_percentile": 0.0004527568817138672,
        "999_percentile": 0.0004527568817138672
    },
    "rpc.reserve_version": {
        "avg": 0.0035811424255371093,
        "sum": 0.017905712127685547,
        "count": 5.0,
        "max": 0.00834035873413086,
        "min": 0.0022764205932617188,
        "std_dev": 0.0026627248096847507,
        "15m_rate": 0.009847214204417167,
        "5m_rate": 0.009847214093446525,
        "1m_rate": 0.009847213945485673,
        "mean_rate": 0.009847213705049297,
        "50_percentile": 0.0024940967559814453,
        "75_percentile": 0.005423545837402344,
        "95_percentile": 0.00834035873413086,
        "99_percentile": 0.00834035873413086,
        "999_percentile": 0.00834035873413086
    },
    "rpc.put_version": {
        "avg": 0.19777460098266603,
        "sum": 0.9888730049133301,
        "count": 5.0,
        "max": 0.23319458961486816,
        "min": 0.18076133728027344,
        "std_dev": 0.022504158404313097,
        "15m_rate": 0.009848085613766367,
        "5m_rate": 0.00984808555364663,
        "1m_rate": 0.009848085484277704,
        "mean_rate": 0.009848085368662829,
        "50_percentile": 0.18417906761169434,
        "75_percentile": 0.22025370597839355,
        "95_percentile": 0.23319458961486816,
        "99_percentile": 0.23319458961486816,
        "999_percentile": 0.23319458961486816
    },
    "rpc.resource_deploy_start": {
        "avg": 0.031178272523880005,
        "sum": 779.4568130970001,
        "count": 25000.0,
        "max": 0.17364263534545898,
        "min": 0.0038547515869140625,
        "std_dev": 0.007585783121374971,
        "15m_rate": 49.262129709034404,
        "5m_rate": 49.262129385027336,
        "1m_rate": 49.2621290378769,
        "mean_rate": 49.26212843614951,
        "50_percentile": 0.031554579734802246,
        "75_percentile": 0.03531104326248169,
        "95_percentile": 0.0457771062850952,
        "99_percentile": 0.06364550828933717,
        "999_percentile": 0.08794155502319337
    },
    "rpc.resource_did_dependency_change": {
        "avg": 0.0711409325504303,
        "sum": 1778.5233137607574,
        "count": 25000.0,
        "max": 1.1705102920532227,
        "min": 0.004614114761352539,
        "std_dev": 0.11562718666996809,
        "15m_rate": 49.266526993194724,
        "5m_rate": 49.2665266922773,
        "1m_rate": 49.26652629876991,
        "mean_rate": 49.26652576637756,
        "50_percentile": 0.06558024883270264,
        "75_percentile": 0.07226765155792236,
        "95_percentile": 0.08944185972213745,
        "99_percentile": 0.12884723186492922,
        "999_percentile": 0.1646015202999116
    },
    "rpc.resource_deploy_done": {
        "avg": 0.03895042956352234,
        "sum": 973.7607390880585,
        "count": 25000.0,
        "max": 0.244920015335083,
        "min": 0.004446744918823242,
        "std_dev": 0.009763166612907406,
        "15m_rate": 49.271892796323634,
        "5m_rate": 49.27189244903559,
        "1m_rate": 49.27189210174755,
        "mean_rate": 49.27189159239176,
        "50_percentile": 0.0394594669342041,
        "75_percentile": 0.043607115745544434,
        "95_percentile": 0.052709341049194336,
        "99_percentile": 0.06945180654525775,
        "999_percentile": 0.15658097243309033
    },
    "self.spec.cpu": {
        "value": 102797
    }
}


"""
