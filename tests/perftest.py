from inmanta.protocol.endpoints import SessionEndpoint
import pytest
import uuid
import time
from tornado import gen
import asyncio
from inmanta import data


class Agent(SessionEndpoint):
    pass


all = ["bono-1.clearwater.local", "bono-2.clearwater.local", "dime-1.clearwater.local", "dime-2.clearwater.local", "ellis-1.clearwater.local", "homer-1.clearwater.local", "homer-2.clearwater.local", "internal", "mgmt.clearwater.local",
       "mon.clearwater.local", "ns-1.clearwater.local", "ns-2.clearwater.local", "openstack", "sprout-1.clearwater.local", "sprout-2.clearwater.local", "vellum-1.clearwater.local", "vellum-2.clearwater.local", "vellum-3.clearwater.local"]


@pytest.mark.asyncio
async def test_agent_performance():
    agent = Agent("node1", 120, 120)
    envid = uuid.UUID("c685cbd5-40cb-4ad9-ae09-d54e4dfab7ae")
    agent.set_environment(envid)
    agent.add_end_point_name("Test")
    await agent.start()
    client = agent._client
    await gen.sleep(2)
    now = time.time()
    status = await asyncio.gather(*[client.get_resources_for_agent(tid=envid, agent=agent,
                                                  incremental_deploy=False) for agent in all])
    print("Full:", time.time() - now)

    now = time.time()
    status = await asyncio.gather(*[client.get_resources_for_agent(tid=envid, agent=agent,
                                                  incremental_deploy=True) for agent in all])
    print("Increment:", time.time() - now)
   