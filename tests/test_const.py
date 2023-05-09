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


from inmanta.const import (
    DONE_STATES,
    INITIAL_STATES,
    NOT_DONE_STATES,
    TRANSIENT_STATES,
    UNDEPLOYABLE_STATES,
    VALID_STATES_ON_STATE_UPDATE,
)


def test_action_set_consistency():

    undep = set(UNDEPLOYABLE_STATES)
    transient = set(TRANSIENT_STATES)
    not_done = set(NOT_DONE_STATES)
    done = set(DONE_STATES)

    initial = set(INITIAL_STATES)
    on_deploy = set(VALID_STATES_ON_STATE_UPDATE)

    # transient is not done
    assert transient <= not_done
    # undeployed is done
    assert undep <= done

    # done + not_done == all == initial states + states one can transition to
    assert done | not_done == on_deploy | initial
