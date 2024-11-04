"""
    Copyright 2024 Inmanta

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

import datetime
import pickle
import uuid

from inmanta.agent.executor import DeployResult, DryrunResult
from inmanta.const import Change, ResourceState
from inmanta.data import LogLine
from inmanta.data.model import AttributeStateChange


def test_risky_objects():
    class EvilString(str):
        """
        This can't be pickled as it is an inner class
        Can be json serialized as it is a string
        """

        pass

    dryrun = DryrunResult(
        "std::Test[a1,k=v],v=3",
        uuid.uuid4(),
        {"a": AttributeStateChange(current="a", desired=EvilString("B"))},
        datetime.datetime.now(),
        datetime.datetime.now(),
        [LogLine(msg="test", args=[], level="INFO", kwargs={"A": EvilString("X")})],
    )
    out = pickle.loads(pickle.dumps(dryrun))

    assert isinstance(out, DryrunResult)
    assert isinstance(out.changes["a"], AttributeStateChange)
    assert isinstance(out.changes["a"].desired, str)
    assert isinstance(out.messages[0], LogLine)

    deploy = DeployResult(
        "std::Test[a1,k=v],v=3",
        uuid.uuid4(),
        ResourceState.deployed,
        [LogLine(msg="test", args=[], level="INFO", kwargs={"A": EvilString("X")})],
        {"a": AttributeStateChange(current="a", desired=EvilString("B"))},
        Change.updated,
    )

    deploy_out = pickle.loads(pickle.dumps(deploy))
    assert isinstance(deploy_out, DeployResult)
    assert isinstance(deploy_out.changes["a"], AttributeStateChange)
    assert isinstance(deploy_out.changes["a"].desired, str)
    assert isinstance(deploy_out.messages[0], LogLine)
    deploy_out.messages[0].log_level
    deploy_out.messages[0].timestamp.timestamp()
