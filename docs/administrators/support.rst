.. only:: iso

    .. _administrators-support:

    *****************
    Support Procedure
    *****************

    1. Create a support archive:
        1. Using the CLI tool:

            1. Log on to the orchestrator machine
            2. Run one of the following commands:

            * if the orchestrator is still running:

                .. code-block:: sh

                    inmanta-support-tool collect-from-server


            * if the orchestrator is not running:

                .. code-block:: sh

                    inmanta-support-tool --config-dir /etc/inmanta/inmanta.dir collect-full
        
        2. Using the web-console:
        
        Use the ``Download support archive`` button at the right top of the ``Home > Status`` page.
        By clicking this button the support archive will be downloaded.

    2. Classify the severity of the incident

    +----------------+----------------+---------------+------------------------------------------------------------------+
    | Severity Level | Service Window | File by phone | Description                                                      |
    +================+================+===============+==================================================================+
    | Urgent         | 24/7           | yes           | Severe negative impact on operations. Unable to use orchestrator |
    +----------------+----------------+---------------+------------------------------------------------------------------+
    | High           | 24/7           | yes           | Degraded ability to use the orchestrator.                        |
    +----------------+----------------+---------------+------------------------------------------------------------------+
    | Normal         | 5/7            |               | Work around is available.                                        |
    +----------------+----------------+---------------+------------------------------------------------------------------+
    | Low            | 5/7            |               | Information request, not related to any error.                   |
    +----------------+----------------+---------------+------------------------------------------------------------------+

    3. Create a support ticket on `support.inmanta.com <https://support.inmanta.com>`_

        1. Log in with your personal support count
        2. Click 'Submit a request'
        3. Describe the problem as best a possible
        4. Attach the archive created by the support tool to the support request

    4. If the severity is high or urgent also contact the support phone number you have received and reference the issue you just created.
