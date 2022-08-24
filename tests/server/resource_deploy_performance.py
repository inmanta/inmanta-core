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
Baseline output
    n_version = 5
    n_resources = 200
    n_deploys = 5


Version 1, Deploy 1: 0:00:17.251966
Version 1, Deploy 2: 0:00:18.656112
Version 1, Deploy 3: 0:00:18.559744
Version 1, Deploy 4: 0:00:18.648354
Version 1, Deploy 5: 0:00:18.194274
Version 2, Deploy 1: 0:00:18.522850
Version 2, Deploy 2: 0:00:18.009620
Version 2, Deploy 3: 0:00:18.123879
Version 2, Deploy 4: 0:00:17.988790
Version 2, Deploy 5: 0:00:18.011786
Version 3, Deploy 1: 0:00:18.340037
Version 3, Deploy 2: 0:00:18.232860
Version 3, Deploy 3: 0:00:18.198341
Version 3, Deploy 4: 0:00:18.331618
Version 3, Deploy 5: 0:00:18.341258
Version 4, Deploy 1: 0:00:18.456327
Version 4, Deploy 2: 0:00:18.309032
Version 4, Deploy 3: 0:00:18.540196
Version 4, Deploy 4: 0:00:18.351061
Version 4, Deploy 5: 0:00:18.607864
Version 5, Deploy 1: 0:00:18.831040
Version 5, Deploy 2: 0:00:18.553836
Version 5, Deploy 3: 0:00:18.466019
Version 5, Deploy 4: 0:00:18.778583
Version 5, Deploy 5: 0:00:18.676939
{
    "rpc.create_project": {
        "avg": 0.0019173622131347656,
        "sum": 0.0019173622131347656,
        "count": 1.0,
        "max": 0.0019173622131347656,
        "min": 0.0019173622131347656,
        "std_dev": 0.0,
        "15m_rate": 0.002178158379933426,
        "5m_rate": 0.0021781583482613134,
        "1m_rate": 0.002178158316589202,
        "mean_rate": 0.0021781582532449818,
        "50_percentile": 0.0019173622131347656,
        "75_percentile": 0.0019173622131347656,
        "95_percentile": 0.0019173622131347656,
        "99_percentile": 0.0019173622131347656,
        "999_percentile": 0.0019173622131347656
    },
    "rpc.create_environment": {
        "avg": 0.00673365592956543,
        "sum": 0.00673365592956543,
        "count": 1.0,
        "max": 0.00673365592956543,
        "min": 0.00673365592956543,
        "std_dev": 0.0,
        "15m_rate": 0.0021781812598819176,
        "5m_rate": 0.002178181242914358,
        "1m_rate": 0.0021781812202909456,
        "mean_rate": 0.002178181196536363,
        "50_percentile": 0.00673365592956543,
        "75_percentile": 0.00673365592956543,
        "95_percentile": 0.00673365592956543,
        "99_percentile": 0.00673365592956543,
        "999_percentile": 0.00673365592956543
    },
    "rpc.heartbeat": {
        "avg": 1.0068154919120942,
        "sum": 452.0601558685303,
        "count": 449.0,
        "max": 1.1168692111968994,
        "min": 0.005121707916259766,
        "std_dev": 0.047799245486186734,
        "15m_rate": 0.978169104552017,
        "5m_rate": 0.9781690964229329,
        "1m_rate": 0.9781690857535102,
        "mean_rate": 0.978169071019546,
        "50_percentile": 1.0087072849273682,
        "75_percentile": 1.0109007358551025,
        "95_percentile": 1.01389741897583,
        "99_percentile": 1.022628903388977,
        "999_percentile": 1.1168692111968994
    },
    "rpc.get_state": {
        "avg": 0.0034018754959106445,
        "sum": 0.006803750991821289,
        "count": 2.0,
        "max": 0.005197286605834961,
        "min": 0.0016064643859863281,
        "std_dev": 0.0025390947416903,
        "15m_rate": 0.004357250115262027,
        "5m_rate": 0.004357250074523288,
        "1m_rate": 0.0043572500315212865,
        "mean_rate": 0.004357249963623392,
        "50_percentile": 0.0034018754959106445,
        "75_percentile": 0.005197286605834961,
        "95_percentile": 0.005197286605834961,
        "99_percentile": 0.005197286605834961,
        "999_percentile": 0.005197286605834961
    },
    "rpc.heartbeat_reply": {
        "avg": 0.000423431396484375,
        "sum": 0.00084686279296875,
        "count": 2.0,
        "max": 0.00046443939208984375,
        "min": 0.00038242340087890625,
        "std_dev": 5.799406355099019e-05,
        "15m_rate": 0.004357261648882298,
        "5m_rate": 0.004357261617196444,
        "1m_rate": 0.004357261578720766,
        "mean_rate": 0.004357261528928712,
        "50_percentile": 0.000423431396484375,
        "75_percentile": 0.00046443939208984375,
        "95_percentile": 0.00046443939208984375,
        "99_percentile": 0.00046443939208984375,
        "999_percentile": 0.00046443939208984375
    },
    "rpc.reserve_version": {
        "avg": 0.00258026123046875,
        "sum": 0.01290130615234375,
        "count": 5.0,
        "max": 0.0033464431762695312,
        "min": 0.0022335052490234375,
        "std_dev": 0.0004419698388829314,
        "15m_rate": 0.010893730722101168,
        "5m_rate": 0.01089373037691516,
        "1m_rate": 0.010893730263739423,
        "mean_rate": 0.010893730088317037,
        "50_percentile": 0.0024313926696777344,
        "75_percentile": 0.002939462661743164,
        "95_percentile": 0.0033464431762695312,
        "99_percentile": 0.0033464431762695312,
        "999_percentile": 0.0033464431762695312
    },
    "rpc.put_version": {
        "avg": 0.17036948204040528,
        "sum": 0.8518474102020264,
        "count": 5.0,
        "max": 0.19280791282653809,
        "min": 0.16378521919250488,
        "std_dev": 0.012560317158113574,
        "15m_rate": 0.010895929565054266,
        "5m_rate": 0.01089592948579926,
        "1m_rate": 0.010895929372577827,
        "mean_rate": 0.010895929236712109,
        "50_percentile": 0.16521859169006348,
        "75_percentile": 0.17913615703582764,
        "95_percentile": 0.19280791282653809,
        "99_percentile": 0.19280791282653809,
        "999_percentile": 0.19280791282653809
    },
    "rpc.resource_deploy_start": {
        "avg": 0.021494613218307496,
        "sum": 107.47306609153748,
        "count": 5000.0,
        "max": 0.09270977973937988,
        "min": 0.0059299468994140625,
        "std_dev": 0.007226247170453662,
        "15m_rate": 10.900908079421427,
        "5m_rate": 10.900907988761487,
        "1m_rate": 10.900907892435303,
        "mean_rate": 10.90090773944666,
        "50_percentile": 0.022053956985473633,
        "75_percentile": 0.025324583053588867,
        "95_percentile": 0.030008566379547116,
        "99_percentile": 0.03718157529830933,
        "999_percentile": 0.07047924280166627
    },
    "rpc.resource_did_dependency_change": {
        "avg": 0.5329061005592346,
        "sum": 2664.530502796173,
        "count": 5000.0,
        "max": 1.4420671463012695,
        "min": 0.01187586784362793,
        "std_dev": 0.3085271418389318,
        "15m_rate": 10.901993256601024,
        "5m_rate": 10.901993171590409,
        "1m_rate": 10.901993058242923,
        "mean_rate": 10.90199290522382,
        "50_percentile": 0.5023475885391235,
        "75_percentile": 0.7225408554077148,
        "95_percentile": 1.0999865174293515,
        "99_percentile": 1.3155424094200137,
        "999_percentile": 1.4418114614486695
    },
    "rpc.resource_deploy_done": {
        "avg": 0.024860311460494996,
        "sum": 124.30155730247498,
        "count": 5000.0,
        "max": 0.08890581130981445,
        "min": 0.0053920745849609375,
        "std_dev": 0.008446695116902391,
        "15m_rate": 10.90502276580904,
        "5m_rate": 10.90502268075117,
        "1m_rate": 10.905022578681729,
        "mean_rate": 10.905022419907045,
        "50_percentile": 0.02637338638305664,
        "75_percentile": 0.030859053134918213,
        "95_percentile": 0.03532253503799438,
        "99_percentile": 0.03857638597488403,
        "999_percentile": 0.0857991156578064
    },
    "self.spec.cpu": {
        "value": 128790
    }
}


"""
