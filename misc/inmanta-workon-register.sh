# Loosely inspired by virtualenv's `activate` and virtualenvwrapper's `virtualenvwrapper.sh`

# TODO: delete old Python implementation
# TODO: write tests, include all failure scenarios
# TODO: document shell and user portability?
# TODO: names of all functions + docstrings and help

if [ "$BASH_SOURCE" = "$0" ]; then
    # TODO: also provide script that can just be executed?
    echo "This script is meant to be sourced rather than executed directly: \`source '$0'\`" >&2
    exit 1
fi

# Locate paths to required executables. Make sure to use executables that live in the same Python environment.
if [ -z "$INMANTA_WORKON_CLI" ]; then
    # get path to inmanta-cli executable
    INMANTA_WORKON_CLI="$(command which inmanta-cli)"
    if [ -z "$INMANTA_WORKON_CLI" ]; then
        echo "Could not find inmanta-cli in PATH" >&2
        return 1
    fi
    # resolve potential symlink
    INMANTA_WORKON_CLI="$(command readlink -e "$INMANTA_WORKON_CLI")"
    if [ -z "$INMANTA_WORKON_CLI" ]; then
        echo "Failed to resolve symlink for inmanta-cli" >&2
        return 1
    fi
fi
if [ -z "$INMANTA_WORKON_PYTHON" ]; then
    # inmanta executable live in same directory as their Python
    INMANTA_WORKON_PYTHON="$(command dirname "$INMANTA_WORKON_CLI")/python3"
    if [ ! -f "$INMANTA_WORKON_PYTHON" ]; then
        echo "Could not find appropriate Python executable" >&2
        return 1
    fi
fi


function __inmanta_workon_environments_dir {
    declare result
    result=$(
        "$INMANTA_WORKON_PYTHON" -c 'import os; from inmanta.config import state_dir; print(os.path.join(state_dir.get(), "server", "environments"));'
    )

    if [ ! "$?" -eq 0 ]; then
        echo "ERROR: Failed to determine server state directory. Is the server config valid?" >&2
        return 1
    fi
    if [ ! -d "$result" ]; then
        echo "WARNING: no environments directory found at '$result'. This is expected if no environments have been compiled yet. Otherwise, make sure you use this function on the server host." >&2
        # only warn, don't return: path might still be valid
    fi

    echo "$result"
    return 0
}


function __inmanta_workon_cli_port {
    declare result
    result=$(
        "$INMANTA_WORKON_PYTHON" -c 'from inmanta.server.config import get_bind_port; print(get_bind_port());' 2> /dev/null
    )

    if [ ! "$?" -eq 0 ]; then
        echo "ERROR: Failed to determine server bind port. Is the server config valid?" >&2
        return 1
    fi

    echo "$result"
    return 0
}


function __inmanta_workon_cli {
    # Call inmanta-cli with appropriate host and port options. Hides stderr.
    declare port
    port="$(__inmanta_workon_cli_port)" || return  # propagate error
    "$INMANTA_WORKON_CLI" --host localhost --port "$port" "$@" 2> /dev/null
}


function inmanta-workon-list {
    # TODO: --help
    __inmanta_workon_cli environment list
    if [ ! "$?" -eq 0 ]; then
        echo "WARNING: Failed to connect through inmanta-cli, falling back to file-based environment discovery." >&2
        declare envs_dir
        envs_dir="$(__inmanta_workon_environments_dir)" || return  # propagate error
        command ls -1 "$(__inmanta_workon_environments_dir)" 2> /dev/null
    fi
    return 0
}


function inmanta-workon-test {
    # TODO: --help
    if [ -z "$1" ] || [ "$1" == "-l" ] || [ "$1" == "--list" ]; then
        inmanta-workon-list
        return
    fi

    declare inmanta_env="$1"
    declare env_id
    declare envs_dir

    envs_dir="$(__inmanta_workon_environments_dir)" || return  # propagate error

    # convert environment argument to environment id
    env_id=$(__inmanta_workon_cli environment show --format '{id}' "$inmanta_env")
    if [ ! "$?" -eq 0 ]; then
        # check if inmanta_env is a valid id
        "$INMANTA_WORKON_PYTHON" -c "import uuid; uuid.UUID('$inmanta_env');" 2> /dev/null
        if [ ! "$?" -eq 0 ]; then
            echo "ERROR: Unable to connect through inmanta-cli to look up environment by name. Please supply its id instead."
            return 1
        fi
        env_id="$inmanta_env"
    fi

    __inmanta_activate "$inmanta_env" "$env_id" "$envs_dir"
}


function __inmanta_activate {
    declare env_name="$1"
    declare env_id="$2"
    declare envs_dir="$3"

    if [ ! -d "$envs_dir/$env_id" ]; then
        echo "ERROR: Directory '$envs_dir/$env_id' does not exist. This may mean the environment has never started a compile" >&2
        return 1
    fi

    # change directory
    command cd "$envs_dir/$env_id"

    activate="$envs_dir/$env_id/.env/bin/activate"
    if [ ! -f "$activate" ]; then
        echo "ERROR: Environment '$envs_dir/$env_id' does not contain a venv. This may mean it has never started a compile" >&2
        return 1
    fi

    # if we are in an active venv, deactivate it first: restores PS1 and triggers our custom deactivate logic if it's an inmanta venv
    declare -F deactivate > /dev/null && deactivate nondestructive
    # store PS1 before sourcing activate because we don't care about virtualenv's modifications
    declare OLD_PS1="$PS1"
    source "$activate"
    export PS1="($env_name) $OLD_PS1"

    __inmanta_workon_register_deactivate

    return 0
}

function __inmanta_workon_register_deactivate {
    # Register a custom deactivate function. Modified from virtualenvwrapper's implementation

    # Save the deactivate function from virtualenv under a different name
    declare original_deactivate
    virtualenv_deactivate=$(declare -f deactivate | sed 's/deactivate/virtualenv_deactivate/g')
    eval "$virtualenv_deactivate"
    unset -f deactivate > /dev/null 2>&1

    # Replace the deactivate() function with a wrapper.
    eval 'deactivate () {
        declare inmanta_env_dir=$(dirname "$VIRTUAL_ENV")
        declare user=${INMANTA_USER:-inmanta}

        # Call the original function.
        virtualenv_deactivate $1
        # no need to restore PS1 because virtualenv_deactivate already does that

        ownership_issues=$(find "$inmanta_env_dir" \! -user "$user" -print -quit)
        if [ -n "$ownership_issues" ]; then
            echo "WARNING: Some files in the environment are not owned by the inmanta user. To fix this, run \`find '\''$inmanta_env_dir'\'' \! -user '\''$user'\'' -exec chown '\''$user'\'':'\''$user'\'' {} \;\` as root." >&2
        fi

        if [ ! "$1" = "nondestructive" ]; then
            # Remove this function
            unset -f virtualenv_deactivate >/dev/null 2>&1
            unset -f deactivate >/dev/null 2>&1
        fi
    }'
}
