Features
=================

A default Inmanta install comes with all features enabled by default. :inmanta.config:option:`config.feature-file` points
to a yaml file that enables or disables features. The format of this file is:

.. code-block:: yaml

    slices:
        slice_name:
            feature_name: bool
