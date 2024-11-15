On Disk Layout
====================

The server stores
 - all data below the state directory, as configured by :inmanta.config:option:`config.state-dir`, which defaults to `/var/lib/inmanta`
 - all logs below the log directory, as configured by  :inmanta.config:option:`config.log-dir`, which defaults to `/var/log/inmanta`


.. code-block::

    /var/lib/inmanta
       ├─ server/
           ├─ .inmanta_use_new_disk_layout   # marker file for new disk layout
           ├─ env_uuid_1/                    # uuid for this environment
           │   ├─ executors/                 # storage are for all executors
           │   │   ├─ venvs/                 # python virtual envs for all executors
           │   │   │  ├─ venv_blueprint_hash_1/
           │   │   │  ├─ venv_blueprint_hash_2/
           │   │   │  ├─ ...
           │   │   ├─ code/                  # Handler code for all executors
           │   │      ├─ executor_blueprint_hash_1/
           │   │      ├─ executor_blueprint_hash_2/
           │   │      ├─ ...
           │   ├─ scheduler.cfg              # Configuration for the scheduler for this environment
           │   ├─ compiler/                  # Folder for the compiler, containing a checkout of the project for this environment
           │   │  ├─ .env                    # symlink to .env-py3.12, updated by the server when required
           │   │  ├─ .env-py3.12             # Virtual env for the compiler to use, with python version
           │
           ├─ env_uuid_2/
           │   ├─ ( ... )
    /var/log/inmanta
       ├─ server.log                         # server main log file
       ├─ resource-actions-env_uuid_1.log    # deploy audit log for environment env_uuid_1, also available via API
       ├─ callback.log                       # log of all http callbacks performed by lsm
       ├─ agent-env_uuid_1.log               # scheduler log for environment env_uuid_1
       ├─ agent-env_uuid_1.out               # stdout for scheduler for environment env_uuid_1, expected to be empty
       ├─ agent-env_uuid_1.err               # stderr for scheduler for environment env_uuid_1, expected to be empty


Cleanup and usage policy
###############################

Most of these files can be safely removed and they will be re-constructed when needed.

In detail, the creation and cleanup policy for every file:


+--------------------------------+-----------------------------------------+-----------------------------+---------------------------------------------------------------------------+
| Path                           | Safe to removed when                    | Reconstructed               | Cleanup                                                                   |
+================================+=========================================+=============================+===========================================================================+
| `.inmanta_use_new_disk_layout` | Always                                  | At server start             |                                                                           |
+--------------------------------+-----------------------------------------+-----------------------------+---------------------------------------------------------------------------+
| `<env_id>`                     |                                         |                             | When environment is cleared or deleted                                    |
+--------------------------------+-----------------------------------------+-----------------------------+---------------------------------------------------------------------------+
| `executors`                    | Server is down or environment is halted | Environment or server start |                                                                           |
+--------------------------------+-----------------------------------------+-----------------------------+---------------------------------------------------------------------------+
| `executors/venvs`              | Server is down or environment is halted | When used                   | controlled by :inmanta.config:option:`agent.executor-venv-retention-time` |
+--------------------------------+-----------------------------------------+-----------------------------+---------------------------------------------------------------------------+
| `executors/code`               | Server is down or environment is halted | When used                   |                                                                           |
+--------------------------------+-----------------------------------------+-----------------------------+---------------------------------------------------------------------------+
| `executors/scheduler.cfg`      | Server is down or environment is halted | When used                   |                                                                           |
+--------------------------------+-----------------------------------------+-----------------------------+---------------------------------------------------------------------------+
| `compiler`                     | When not compiling                      | When performing a recompile |                                                                           |
+--------------------------------+-----------------------------------------+-----------------------------+---------------------------------------------------------------------------+
| `compiler/.env`                | When not compiling                      | When performing a recompile |                                                                           |
+--------------------------------+-----------------------------------------+-----------------------------+---------------------------------------------------------------------------+
| `compiler/.env-py3.12`         | When no longer targeted by  `.env`      | When performing a recompile |                                                                           |
+--------------------------------+-----------------------------------------+-----------------------------+---------------------------------------------------------------------------+
