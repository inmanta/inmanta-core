# TODO: if applicable, mention virtualenvwrapper inspiration
# TODO: ask about shell portability. Currently only sh/bash is guaranteed to work. Seems acceptable to me


# TODO: name + read from config?
ENVIRONMENTS_DIR=/var/lib/inmanta/server/environments

# TODO: names of all functions
# TODO: inmanta-cli executable always available and correct path?


function inmanta-workon-list {
    # TODO: use configured port?
    # TODO: log "falling back to file-based discovery" when API call fails
    # TODO: mention reasoning for "command ls" vs "ls"
    inmanta-cli --host localhost environment list 2>/dev/null || command ls -1 "$ENVIRONMENTS_DIR"
    return 0
}


function inmanta-workon-test {
    # TODO: --help
    # TODO: call it env-id instead?
    if [ -z "$1" ] || [ "$1" == "-l" ] || [ "$1" == "--list" ]; then
        inmanta-workon-list
        return $?
    fi
    declare inmanta_env="$1"

    # TODO: log "falling back to ..." when API call fails
    env_id=$(inmanta-cli environment show --format '{id}' "$inmanta_env") || env_id="$inmanta_env"

    if [ ! -d "$ENVIRONMENTS_DIR/$env_id" ]; then
        echo "ERROR: Directory '$ENVIRONMENTS_DIR/$env_id' does not exist. This may mean the environment has never started a compile" >&2
        return 1
    fi

    command cd "$ENVIRONMENTS_DIR/$env_id"

    activate="$ENVIRONMENTS_DIR/$env_id/.env/bin/activate"
    if [ ! -f "$activate" ]; then
        # TODO update error message
        echo "ERROR: Environment '$ENVIRONMENTS_DIR/$env_id' does not contain a venv. This may mean it has never started a compile" >&2
        return 1
    fi
    # TODO: register custom deactivate
    source "$activate"

    # TODO: custom PS1?
}
