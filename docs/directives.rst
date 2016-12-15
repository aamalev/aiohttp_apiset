Directives
==========

Extends specification with directives $include, $view and $handler.

$handler
^^^^^^^^

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


$include
^^^^^^^^

Root spec:

.. code-block:: yaml

    swagger: '2.0'

    basePath: /api/1

    paths:

      /user:
        - $include: swagger/user.yaml
        - $include: ...
        - $include: ...

Nested spec in file swagger/user.yaml:

.. code-block:: yaml

    swagger: '2.0'

    paths:
      /profile:
        get:
          $handler: mymodule.handler
      /{id:\d+}:
        get:
          $handler: mymodule.handler2
