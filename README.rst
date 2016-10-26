==============
aiohttp_apiset
==============

.. image:: https://travis-ci.org/aamalev/aiohttp_apiset.svg?branch=master
    :target: https://travis-ci.org/aamalev/aiohttp_apiset

.. image:: https://badge.fury.io/py/aiohttp_apiset.svg
    :target: https://badge.fury.io/py/aiohttp_apiset

Package to build routes using swagger specification.

Extends specification with directives $include, $view and $handler.

Features
--------

- Building of the routing from specification swagger
- Using inclusions other specifications with concatenate url
- Optional output of the resulting specification and view embed swagger-ui
- Advanced router with TreeResource
- Extract specify parameters from request and validate with jsonschema
- Serialize data as response with middleware


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

Create router:

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

  Application(router=router)
