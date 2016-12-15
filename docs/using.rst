
======================
Using with application
======================

The basis of the package is the class SwaggerRouter.

.. code-block:: python

  from aiohttp_apiset import SwaggerRouter


Create router
^^^^^^^^^^^^^

.. code-block:: python

  router = SwaggerRouter(
      'data/root.yaml',
      search_dirs=['routes'])

Use router
^^^^^^^^^^

.. code-block:: python

  Application(router=router)
