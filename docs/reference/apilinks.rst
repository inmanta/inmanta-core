API self-referencing links
==========================

Some API endpoints can provide additional information or context by returning links to other API endpoints.
The following table documents all these links and their format:


.. list-table:: Self-referencing links
   :header-rows: 1

   * - Link target type
     - Link format
   * - Compile report
     - ``/api/v2/compilereport/<compile_id>``
   * - Managed resource
     - ``/api/v2/resource/<resource_id>``
