package default_policy

# Write the information about the endpoint into a variable
# to make the policy easier to read.
endpoint_data := data.endpoints[input.request.endpoint_id]

# The environment used in the request
request_environment := input.request.parameters[endpoint_data.environment_param] if {
    endpoint_data.environment_param != null
} else := null

# Don't allow anything that is not explicitly allowed.
default allowed := false

# TODO: Do we remove the read-only flag?

### General rules ###

# Every user can change its own password
allowed if {
    input.request.endpoint_id == "PATCH /api/v2/user/<username>/password"
    input.token.sub == input.request.parameters.username
}

# Any authenticated user is allowed read-only access on the environment independent endpoints.
allowed if {
    endpoint_data.read_only
    endpoint_data.environment_param == null
}

### Role: read-only ###

# Users with the read-only role can execute all read-only endpoints on that environment.

read_only_labels := {
    "agent.read",
    "compilereport.read",
    "compiler.status.read",
    "desired-state.read",
    "discovered_resources.read",
    "docs.read",
    "dryrun.read",
    "environment.read",
    "environment.settings.read",
    "fact.read",
    "files.read",
    "graphql.read",
    "metrics.read",
    "notification.read",
    "parameter.read",
    "pip_config.read",
    "project.read",
    "resources.read",
    "status.read",
    "lsm.callback.read",
    "lsm.catalog.read",
    "lsm.docs.read",
    "lsm.instance.read",
    "lsm.order.read",
    "support.support-archive.read",
    "graphql.read",
}

allowed if {
    "read-only" in input.token["urn:inmanta:roles"][request_environment]
    endpoint_data.auth_label in read_only_labels
}


#{
#    "agent.read",
#    # TODO: endpoint still used
#    #"agent.write",
#    "auth.admin",
#    "auth.change-password",
#    "compilereport.read",
#    "compiler.execute",
#    "compiler.status.read",
#    "deploy",
#    "desired-state.read",
#    "desired-state.write",
#    "discovered_resources.read",
#    "docs.read",
#    "dryrun.read",
#    "dryrun.write",
#    "executor.halt-resume",
#    "environment.halt-resume",
#    "environment.read",
#    "environment.create",
#    "environment.modify",
#    "environment.delete",
#    "environment.clear",
#    "environment.settings.read",
#    "environment.settings.write",
#    "fact.read",
#    "fact.write",
#    "files.read",
#    "files.write",
#    "graphql.read",
#    "metrics.read",
#    "notification.read",
#    "notification.write",
#    "parameter.read",
#    "parameter.write",
#    "pip_config.read",
#    "project.read",
#    "project.create",
#    "project.modify",
#    "project.delete",
#    "resources.read",
#    "status.read",
#    "token",
#
#    "lsm.callback.read",
#    "lsm.callback.write",
#    "lsm.catalog.read",
#    "lsm.catalog.write",
#    "lsm.docs.read",
#    "lsm.expert.write",
#    "lsm.instance.migrate",
#    "lsm.instance.read",
#    "lsm.instance.write",
#    "lsm.order.read",
#    "lsm.order.write",
#
#    "support.support-archive.read",
#}

## Role: noc ###

# Can do all operations that do not alter the desired state or modify the settings.

noc_specific_labels := {
    "compiler.execute",
    "deploy",
    "dryrun.write",
    "executor.halt-resume",
    "environment.halt-resume",
    "notification.write",
}
all_noc_labels := {
    label | some set in {read_only_labels, noc_specific_labels} some label in set
}

allowed if {
    "noc" in input.token["urn:inmanta:roles"][request_environment]
    endpoint_data.auth_label in all_noc_labels
}


### Role: operator ###

operator_specific_labels := {
    "lsm.instance.write",
    "lsm.order.write",
}
all_operator_labels := {
    label | some set in {all_noc_labels, operator_specific_labels} some label in set
}

allowed if {
    "operator" in input.token["urn:inmanta:roles"][request_environment]
    endpoint_data.auth_label in all_operator_labels
}


### Role: environment-admin ###

# Can do schema updates, update-and-recompile, setting updates, but no expert mode

admin_specific_labels := {
    "desired-state.write",
    "environment.modify",
    "environment.settings.write",
    "lsm.callback.write",
    "lsm.catalog.write",
    "lsm.instance.migrate",
}

all_admin_labels := {
    label | some set in {all_operator_labels, admin_specific_labels} some label in set
}

allowed if {
    "environment-admin" in input.token["urn:inmanta:roles"][request_environment]
    endpoint_data.auth_label in all_admin_labels
}


### Role: environment-expert-admin ###

# Can do everything including expert mode.

expert_admin_specific_labels := {
    "lsm.expert.write",
    "environment.clear",
    "environment.delete",
}

all_expert_admin_labels := {
    label | some set in {all_operator_labels, expert_admin_specific_labels} some label in set
}

allowed if {
    "environment-expert-admin" in input.token["urn:inmanta:roles"][request_environment]
    endpoint_data.auth_label in all_expert_admin_labels
}

# Users can only create tokens scoped to the environment they are authorized for.
allowed if {
    "environment-expert-admin" in input.token["urn:inmanta:roles"][request_environment]
    endpoint_data.auth_label == "token"
    input.request.parameters.tid == request_environment
}


### Role: global admin ###

# Allow access to everything. This admin role is not scoped to a specific environment.
# Users with this privilege can also create/delete project and environments and add/delete users, etc.

allowed if {
    input.token["urn:inmanta:is_admin"]
}


# TODO: Assert that the intersection of the different sets is empty
#count(read_only_labels) + count(all_noc_labels) + count(all_operator_labels) + count(all_admin_labels) + count(all_expert_admin_labels) == count(read_only_labels | all_noc_labels | all_operator_labels | all_admin_labels | all_expert_admin_labels)

