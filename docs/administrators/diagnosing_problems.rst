Diagnosing problems
###################

When an unexpected problem arises with an inmanta environment, you might want to work directly on the environment on the
orchestrator host to diagnose it. The ``inmanta-workon`` command, installed by the RPM, provides that functionality.
``inmanta-workon myenvironment`` puts you in the environment's project directory and activates its Python venv. If you don't
know the name of the environment by heart, ``inmanta-workon --list`` gives an overview of all environments on the server.

For more details, see ``inmanta-workon --help``.

.. note::
    If you didn't install inmanta from RPM, you can manually source the ``inmanta-workon-register.sh`` script to get
    access to the ``inmanta-workon`` command. You can find the script in the ``misc`` directory in the ``inmanta-core``
    git repository.
