==============
aiohttp_apiset
==============

Package to build routes using swagger specification.

Extends specification with directives $include, $view and $handler.

-------
Usecase
-------

$handler
========

Handler:

.. code-block:: python

  from aiohttp import web

  async def handler(request):
      return web.json_response(
          {'test': 'Hello'}
      )

Swagger spec:

.. code-block:: yaml

    swagger: '2.0'

    basePath: /api/1

    paths:

      /hello:
        get:
          $handler: mymodule.handler
          summary: and other not required for working route

Equal:

.. code-block:: python

  app.router.add_route(
      'GET',
      '/api/1/hello',
      handler,
      name='mymodule.handler')

To setup route to use in application:

setup to application
====================

.. code-block:: python

  from aiohttp_apiset import SwaggerRouter

  router = SwaggerRouter(
      'data/root.yaml',
      search_dirs=['routes'])
  router.setup(app)
