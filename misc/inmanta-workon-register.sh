# Loosely inspired by virtualenv's `activate` and virtualenvwrapper's `virtualenvwrapper.sh`

if [ -z "$BASH" ]; then
    echo "WARNING: This script was written for bash and might not be portable to other shells" >&2
fi
if [ "$BASH_SOURCE" = "$0" ]; then
    echo "ERROR: This script is meant to be sourced rather than executed directly: \`source '$0'\`" >&2
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


function inmanta-workon {
    if [ -z "$1" ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
        command cat <<EOF
Usage: inmanta-workon [-l | --list] [ENVIRONMENT]
Activate the Python virtual environment for an inmanta environment.

-l, --list      list the inmanta environments on this server

The ENVIRONMENT argument may be the name or the id of an inmanta environment.
EOF
        return 0
    fi
    if [ "$1" == "-l" ] || [ "$1" == "--list" ]; then
        __inmanta_workon_list
        return
    fi

    declare inmanta_env="$1"
    declare env_id
    declare envs_dir

    envs_dir="$(__inmanta_workon_environments_dir)" || return  # propagate error

    # convert environment argument to environment id
    env_id=$(__inmanta_workon_cli environment show --format '{id}' "$inmanta_env")
    if [ ! "$?" -eq 0 ]; then
        # differentiate between invalid name or broken inmanta-cli
        __inmanta_workon_cli environment list > /dev/null
        if [ "$?" -eq 0 ]; then
            echo "ERROR: Environment '$inmanta_env' could not be uniquely identified. Available environments are:" >&2
            __inmanta_workon_list >&2
            return 1
        else
            # check if inmanta_env is a valid id, if so we can fall back on file-based workon
            "$INMANTA_WORKON_PYTHON" -c "import uuid; uuid.UUID('$inmanta_env');" 2> /dev/null
            if [ ! "$?" -eq 0 ]; then
                echo "ERROR: Unable to connect through inmanta-cli to look up environment by name. Please supply its id instead." >&2
                return 1
            fi
            env_id="$inmanta_env"
        fi
    fi

    __inmanta_workon_activate "$inmanta_env" "$env_id" "$envs_dir"
}

function __store_old_config {
    #  Store config before activation to be later restored in __restore_old_config during deactivation

    # Store INMANTA_CONFIG_ENVIRONMENT
    if [ -n "${INMANTA_CONFIG_ENVIRONMENT:-}" ] ; then
        _OLD_INMANTA_CONFIG_ENVIRONMENT="${INMANTA_CONFIG_ENVIRONMENT:-}"
    fi
    # Store pip configuration
    if [ -n "${PIP_PRE:-}" ] ; then
        _OLD_INMANTA_CONFIG_PIP_PRE="${PIP_PRE:-}"
    fi

    if [ -n "${PIP_INDEX_URL:-}" ] ; then
        _OLD_INMANTA_CONFIG_PIP_INDEX_URL="${PIP_INDEX_URL:-}"
    fi

    if [ -n "${PIP_EXTRA_INDEX_URL:-}" ] ; then
        _OLD_INMANTA_CONFIG_PIP_EXTRA_INDEX_URL="${PIP_EXTRA_INDEX_URL:-}"
    fi

    if [ -n "${PIP_CONFIG_FILE:-}" ] ; then
        _OLD_INMANTA_CONFIG_PIP_CONFIG_FILE="${PIP_CONFIG_FILE:-}"
    fi

    return 0
}

function __restore_old_config {
    # Reset the config in the state it was before activation (saved in __store_old_pip_config)

    if [ -n "${_OLD_INMANTA_CONFIG_ENVIRONMENT:-}" ] ; then
        # Another env was active prior to inmanta-workon call: restore INMANTA_CONFIG_ENVIRONMENT to its old value
        INMANTA_CONFIG_ENVIRONMENT="${_OLD_INMANTA_CONFIG_ENVIRONMENT:-}"
        export INMANTA_CONFIG_ENVIRONMENT
        unset _OLD_INMANTA_CONFIG_ENVIRONMENT
    else
        unset INMANTA_CONFIG_ENVIRONMENT
    fi

    # Restore pip configuration
    if [ -n "${_OLD_INMANTA_CONFIG_PIP_PRE:-}" ] ; then
        PIP_PRE="${_OLD_INMANTA_CONFIG_PIP_PRE:-}"
        export PIP_PRE
        unset _OLD_INMANTA_CONFIG_PIP_PRE
    else
        unset PIP_PRE
    fi

    if [ -n "${_OLD_INMANTA_CONFIG_PIP_INDEX_URL:-}" ] ; then
        PIP_INDEX_URL="${_OLD_INMANTA_CONFIG_PIP_INDEX_URL:-}"
        export PIP_INDEX_URL
        unset _OLD_INMANTA_CONFIG_PIP_INDEX_URL
    else
        unset PIP_INDEX_URL
    fi

    if [ -n "${_OLD_INMANTA_CONFIG_PIP_EXTRA_INDEX_URL:-}" ] ; then
        PIP_EXTRA_INDEX_URL="${_OLD_INMANTA_CONFIG_PIP_EXTRA_INDEX_URL:-}"
        export PIP_EXTRA_INDEX_URL
        unset _OLD_INMANTA_CONFIG_PIP_EXTRA_INDEX_URL
    else
        unset PIP_EXTRA_INDEX_URL
    fi

    if [ -n "${_OLD_INMANTA_CONFIG_PIP_CONFIG_FILE:-}" ] ; then
        PIP_CONFIG_FILE="${_OLD_INMANTA_CONFIG_PIP_CONFIG_FILE:-}"
        export PIP_CONFIG_FILE
        unset _OLD_INMANTA_CONFIG_PIP_CONFIG_FILE
    else
        unset PIP_CONFIG_FILE
    fi

    return 0
}


function __get_pip_config {
    python_script=$(cat << END
from inmanta.module import Project, ProjectConfigurationWarning
import warnings
warnings.filterwarnings("error", category=ProjectConfigurationWarning)
try:
    project=Project('.', autostd=False)
except ProjectConfigurationWarning:
    exit(1)
pip_cfg=project.metadata.pip.model_dump()
for k in ['pre','index_url','use_system_config']:
    print(pip_cfg[k]) if pip_cfg[k] is not None else print('')
print(' '.join(pip_cfg['extra_index_url']))
END
)

    result=$("$INMANTA_WORKON_PYTHON" -c "${python_script}")

    if [ ! "$?" -eq 0 ]; then
        echo "WARNING: Invalid project.yml pip configuration" >&2
        return 1
    fi

    echo "$result"
    return 0
}

function __set_pip_config {
    declare pre
    declare index_url
    declare extra_index_url
    declare use_system_config

    pip_config="$(__get_pip_config)" || return 0

    mapfile -t arrIN <<< "$pip_config"
    pre=${arrIN[0]}
    index_url=${arrIN[1]}
    use_system_config=${arrIN[2]}
    extra_index_url=${arrIN[3]}

    if [ "$use_system_config" == "False" ] ; then
        if [ -z "$index_url" ] ; then
            # Do not override any config because unsetting the config and the index urls might lead to PyPi being used, which is worse than keeping the config
            echo "WARNING: Cannot use project.yml pip configuration: pip.use-system-config is False, but no index is defined in the pip.index-url section of the project.yml" >&2
            return 0
        fi
        # Override values set in the config
        PIP_INDEX_URL="${index_url:-}"
        export PIP_INDEX_URL

        PIP_EXTRA_INDEX_URL="${extra_index_url:-}"
        export PIP_EXTRA_INDEX_URL

        PIP_PRE="${pre:-}"
        export PIP_PRE

        # Make sure we disable the config
        PIP_CONFIG_FILE="/dev/null"
        export PIP_CONFIG_FILE
    else
        if [ -n "${index_url:-}" ] ; then
            PIP_INDEX_URL="${index_url:-}"
            export PIP_INDEX_URL
        fi
        if [ -n "${pre:-}" ] ; then
            PIP_PRE="${pre:-}"
            export PIP_PRE
        fi
        # Append to existing extra indexes
        if [ -n "${extra_index_url:-}" ] ; then
            PIP_EXTRA_INDEX_URL="${PIP_EXTRA_INDEX_URL:+${PIP_EXTRA_INDEX_URL} }${extra_index_url}"
            export PIP_EXTRA_INDEX_URL
        fi
    fi

    return 0
}

function __inmanta_workon_environments_dir {
    # Writes the path to the server's environments directory to stdout

    declare result
    result=$(
        "$INMANTA_WORKON_PYTHON" -c 'import os; from inmanta.config import state_dir; print(os.path.join(state_dir.get(), "server", "environments"));' 2> /dev/null
    )

    if [ ! "$?" -eq 0 ]; then
        echo "ERROR: Failed to determine server state directory. Is the server config valid?" >&2
        return 1
    fi
    if [ ! -d "$result" ]; then
        # only warn, don't return: path might still be valid
        echo "WARNING: no environments directory found at '$result'. This is expected if no environments have been compiled yet. Otherwise, make sure you use this function on the server host." >&2
    fi

    echo "$result"
    return 0
}


function __inmanta_workon_cli_port {
    # Writes the configured server port to stdout

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
    # Calls inmanta-cli with appropriate host and port options

    declare port
    port="$(__inmanta_workon_cli_port)" || return  # propagate error
    "$INMANTA_WORKON_CLI" --host localhost --port "$port" "$@" 2> /dev/null
}


function __inmanta_workon_list {
    # Writes a list of environments to stdout. Attempts to print a nice table if inmanta-cli works, otherwise falls back to a plain uuid list.

    __inmanta_workon_cli environment list
    if [ ! "$?" -eq 0 ]; then
        echo "WARNING: Failed to connect through inmanta-cli, falling back to file-based environment discovery." >&2
        declare envs_dir
        envs_dir="$(__inmanta_workon_environments_dir)" || return  # propagate error
        command ls -1 "$envs_dir" 2> /dev/null
    fi
    return 0
}


function __inmanta_workon_activate {
    # Check user
    declare current_user=$(whoami)
    if [[ "${current_user}" != "root" && "${current_user}" != ${INMANTA_USER:-inmanta} ]]; then
        echo "WARNING: The inmanta-workon tool should be run as either root or the inmanta user to have write access (to be able to run pip install or inmanta project install)." >&2
    fi

    # Activates the environment's venv and registers the deactivate function

    declare env_name="$1"
    declare env_id="$2"
    declare envs_dir="$3"

    if [ ! -d "$envs_dir/$env_id" ]; then
        echo "ERROR: Directory '$envs_dir/$env_id' does not exist. This may mean the environment has never started a compile." >&2
        return 1
    fi

    # change directory
    command cd "$envs_dir/$env_id"

    activate="$envs_dir/$env_id/.env/bin/activate"
    if [ ! -f "$activate" ]; then
        echo "ERROR: Environment '$envs_dir/$env_id' does not contain a venv. This may mean it has never started a compile." >&2
        return 1
    fi

    # if we are in an active venv, deactivate it first: restores PS1 and triggers our custom deactivate logic if it's an inmanta venv
    declare -F deactivate > /dev/null && deactivate
    # store PS1 before sourcing activate because we don't care about virtualenv's modifications
    declare OLD_PS1="$PS1"

    # store config before activation
    __store_old_config
    __set_pip_config

    export INMANTA_CONFIG_ENVIRONMENT=$env_id

    source "$activate"
    export PS1="($env_name) $OLD_PS1"


    eval 'inmanta () { python3 -m inmanta.app "$@"; }' # workaround for #4259

    echo "WARNING: Make sure you exit the current environment by running the 'deactivate' command rather than simply exiting the shell. This ensures the proper permission checks are performed." >&2
    __inmanta_workon_register_deactivate
}


function __inmanta_workon_register_deactivate {
    # Registers a custom deactivate function. Modified from virtualenvwrapper's implementation

    # Save the deactivate function from virtualenv under a different name
    declare virtualenv_deactivate
    virtualenv_deactivate=$(declare -f deactivate | sed 's/deactivate/virtualenv_deactivate/g')

    eval "$virtualenv_deactivate"
    unset -f deactivate > /dev/null 2>&1


    # Replace the deactivate() function with a wrapper.
    eval 'deactivate () {

        declare inmanta_env_dir=$(dirname "$VIRTUAL_ENV")
        declare user=${INMANTA_USER:-inmanta}

        # Call the original function.
        virtualenv_deactivate "$1"

        unset -f inmanta >/dev/null 2>&1
        # no need to restore PS1 because virtualenv_deactivate already does that

        __restore_old_config

        ownership_issues=$(find "$inmanta_env_dir" \! -user "$user" -print -quit)
        if [ -n "$ownership_issues" ]; then
            echo "WARNING: Some files in the environment are not owned by the $user user. To fix this, run \`chown -R $user:$user '\''$inmanta_env_dir'\''\` as root." >&2
        fi

        if [ ! "$1" = "nondestructive" ]; then
            # Remove this function
            unset -f virtualenv_deactivate >/dev/null 2>&1
            unset -f deactivate >/dev/null 2>&1
        fi
    }'
}
