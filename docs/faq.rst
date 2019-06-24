Frequently asked questions
==========================

How do I use Inmanta with a http/https proxy?
    Use the http_proxy and https_proxy environment variables to specify the proxy server to use. For the server installed from
    our RPMs, add the environment variable to the systemd unit file. Copy inmanta-server.service from /lib/systemd/systemd/system
    to /etc/systemd/system and add the following lines to the [Service] section with the correct proxy server details::


        Environment=http_proxy=1.2.3.4:5678
        Environment=https_proxy=1.2.3.4:5678

    Afterwards run systemctl daemon-reload and restart the inmanta server.


I get a click related error/exception when I run inmanta-cli.
    The following error is shown::

        Traceback (most recent call last):
            File "/usr/bin/inmanta-cli", line 11, in <module>
                sys.exit(main())
            File "/opt/inmanta/lib64/python3.4/site-packages/inmanta/main.py", line 871, in main
                cmd()
            File "/opt/inmanta/lib64/python3.4/site-packages/click/core.py", line 722, in __call__
                return self.main(*args, **kwargs)
            File "/opt/inmanta/lib64/python3.4/site-packages/click/core.py", line 676, in main
                _verify_python3_env()
            File "/opt/inmanta/lib64/python3.4/site-packages/click/_unicodefun.py", line 118, in _verify_python3_env
                'for mitigation steps.' + extra)
        RuntimeError: Click will abort further execution because Python 3 was configured to use ASCII as encoding for the environment.  Consult http://click.pocoo.org/python3/for mitigation steps.


    This error occurs when the locale are not set correctly. Make sure that LANG and LC_ALL are set. For example::

        export LC_ALL=en_US.utf8
        export LANG=en_US.utf8


The model does not compile and exits with "could not complete model".
    There is an upperbound on the number of iterations used in the model transformation algorithm. For large models this might
    not be enough. This limit is controlled with the environment variable INMANTA_MAX_ITERATIONS The default value is set to
    10000 iterations.
