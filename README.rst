==============
aiohttp_apiset
==============

.. image:: https://travis-ci.org/aamalev/aiohttp_apiset.svg?branch=master
    :target: https://travis-ci.org/aamalev/aiohttp_apiset

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


Setup to application
====================

To setup route to use in application:

.. code-block:: python

  from aiohttp_apiset import SwaggerRouter

  router = SwaggerRouter(
      'data/root.yaml',
      search_dirs=['routes'])

Setup to application:

.. code-block:: python

  router.setup(app)

or use as router:

.. code-block:: python

  Application(route=router)
