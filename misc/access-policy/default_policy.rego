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


### General rules ###

# Every user can change its own password
allowed if {
    input.request.endpoint_id == "PATCH /api/v2/user/<username>/password"
    input.token.sub == input.request.parameters.username
}

# An admin can change any user's password
allowed if {
    input.request.endpoint_id == "PATCH /api/v2/user/<username>/password"
    input.token["urn:inmanta:is_admin"]
}

# Any authenticated user has read-only access on the environment-independent endpoints
allowed if {
    endpoint_data.read_only
    endpoint_data.environment_param == null
}


### Role: read-only ###

# If the user has the read-only role on a certain environment, he/she can invoke all read-only endpoints for that environment.
allowed if {
    input.token["urn:inmanta:roles"][request_environment] == "read_only"
    endpoint_data.read_only
}


### Role: admin ###

# Admin role provides access to everything
allowed if {
    input.token["urn:inmanta:is_admin"]
}


### Role: environment-admin ###

allowed if {
    input.token["urn:inmanta:roles"][request_environment] == "environment_admin"
    endpoint_data.auth_label != "project.write"
    # Creating, deleting and clearing environments is reserved for admins only.
    not input.request.endpoint_id in {"PUT /api/v1/environment", "DELETE /api/v1/environment/<id>", "DELETE /api/v1/decommission/<id>", "PUT /api/v2/environment", "DELETE /api/v2/environment/<id>", "DELETE /api/v2/decommission/<id>"}
}


### Role: lsm_user ###

# End-users can only provision service instances
allowed if {
    input.token["urn:inmanta:roles"][request_environment] == "lsm_user"
    endpoint_data.auth_label in {"lsm.order.read", "lsm.order.write", "catalog.read", "instance.read", "instance.write"}
}

# Allow read-only access on everything in that environment.
allowed if {
    input.token["urn:inmanta:roles"][request_environment] == "lsm_user"
    endpoint_data.read_only
    # lsm_users cannot create a support archive
    endpoint_data.auth_label != "support.support-archive.read"
}


### Role: noc ###

# Allow halt/resume of environments/agents
allowed if {
    input.token["urn:inmanta:roles"][request_environment] == "noc"
    endpoint_data.auth_label == "environment.halt-resume"
}

# Allow read-only access on everything in that environment.
allowed if {
    input.token["urn:inmanta:roles"][request_environment] == "noc"
    endpoint_data.read_only
}


### Role: ops ###

# Operations people can do anything, but no expert mode features
allowed if {
    input.token["urn:inmanta:roles"][request_environment] == "ops"
    endpoint_data.auth_label != "lsm.expert.write"
    not is_enable_expert_mode_env_settings 
}

# Allow read-only access on everything in that environment.
allowed if {
    input.token["urn:inmanta:roles"][request_environment] == "ops"
    endpoint_data.read_only
}


### Utility rules ###

is_enable_expert_mode_env_settings if {
    input.request.endpoint_id in {"POST /api/v1/environment_settings/{id}", "POST /api/v2/environment_settings/{id}", "DELETE /api/v1/environment_settings/{id}", "DELETE /api/v2/environment_settings/{id}"}
    input.request.parameters.id == "enable_lsm_expert_mode"
    input.request.parameters.value = true
}

