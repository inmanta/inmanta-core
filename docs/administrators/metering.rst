.. _metering-setup:

Performance Metering
====================

This guide explains how to send performance metrics about the inmanta server to influxdb.

The inmanta server has a built-in `pyformance <https://github.com/omergertel/pyformance>`_ instrumentation for all
API endpoints and supports sending the results to influxdb.


Configuration summary
---------------------

To enable performance reporting, set the options as found under :inmanta.config:group:`influxdb` in the server
configuration file.

For example:

.. code-block:: ini

    [influxdb]
    # The hostname of the influxdb server
    host = localhost
    # The port of the influxdb server
    port = 8086
    # The name of the database on the influxdb server
    name = inmanta
    tags= environment=prod,az=a


Setup guide
-----------

#. To install influxdb, follow the instructions found at `docs.influxdata.com <https://docs.influxdata.com/influxdb/v1.7/introduction/installation#installing-influxdb-oss>`_.
#. Create a database to send the data to:

    .. code-block:: sh

        influx
        CREATE DATABASE inmanta

#. Update the inmanta config file, add the following block

    .. code-block:: ini

        [influxdb]
        # The hostname of the influxdb server
        host = localhost
        # The port of the influxdb server
        port = 8086
        # The name of the database on the influxdb server
        name = inmanta

#. Restart the inmanta server.
#. [optional] install grafana, follow the instructions found at `<https://grafana.com/grafana/download>`_
#. [optional] load the inmanta dashboard found at `<https://grafana.com/dashboards/10089>`_

Reported Metrics
----------------

This section assumes familiarity with influxdb. See `here <https://docs.influxdata.com/influxdb/v1.7/concepts/key_concepts/#field-key>`_.

All API metrics are reported under the measurement `metrics`.

The API endpoint is attached as a tag called `key`.
The API endpoint is reported as the server method, to know which url corresponds to which method, please consult
`methods.py <https://github.com/inmanta/inmanta/blob/master/src/inmanta/protocol/methods.py>`_.

The fields available for each API endpoint are (cfr `metrics timer <https://metrics.dropwizard.io>`_):

+-----------------+-------+--------------------------------------------------------------------------+
| field           | type  | description                                                              |
+=================+=======+==========================================================================+
| 15m_rate        | float | fifteen-minute exponentially-weighted moving average of the request rate |
+-----------------+-------+--------------------------------------------------------------------------+
| 5m_rate         | float | five-minute                                                              |
|                 |       | exponentially-weighted moving average of the request rate                |
+-----------------+-------+--------------------------------------------------------------------------+
| 1m_rate         | float | one-minute                                                               |
|                 |       | exponentially-weighted moving average of the request rate                |
+-----------------+-------+--------------------------------------------------------------------------+
| mean_rate       | float | mean of the request rate                                                 |
+-----------------+-------+--------------------------------------------------------------------------+
| min             | float | minimal observed request latency                                         |
+-----------------+-------+--------------------------------------------------------------------------+
| 50_percentile   | float | median (50 percentile) observed request latency                          |
+-----------------+-------+--------------------------------------------------------------------------+
| 75_percentile   | float | 75 percentile observed request latency                                   |
+-----------------+-------+--------------------------------------------------------------------------+
| 95_percentile   | float | 95 percentile observed request latency                                   |
+-----------------+-------+--------------------------------------------------------------------------+
| 99_percentile   | float | 99 percentile observed request latency                                   |
+-----------------+-------+--------------------------------------------------------------------------+
| 999_percentile  | float | 999 percentile observed request latency                                  |
+-----------------+-------+--------------------------------------------------------------------------+
| max             | float | maximal observed request latency                                         |
+-----------------+-------+--------------------------------------------------------------------------+
| avg             | float | average observed latency                                                 |
+-----------------+-------+--------------------------------------------------------------------------+
| std_dev         | float | standard deviation of the observed latency                               |
+-----------------+-------+--------------------------------------------------------------------------+
| count           | float | number of calls seen since server start                                  |
+-----------------+-------+--------------------------------------------------------------------------+
| sum             | float | total wall-time spent executing this call since server start             |
+-----------------+-------+--------------------------------------------------------------------------+
