from inmanta.const import (
    TRANSIENT_STATES,
    UNDEPLOYABLE_STATES,
    NOT_DONE_STATES,
    VALID_STATES_ON_STATE_UPDATE,
    DONE_STATES,
    INITIAL_STATES,
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
