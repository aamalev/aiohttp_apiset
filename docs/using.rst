==============================
Using with aiohttp application
==============================

The basis of the package is the class SwaggerRouter.

.. code-block:: python

  from aiohttp_apiset import SwaggerRouter


Create router
^^^^^^^^^^^^^

.. code-block:: python

  base = pathlib.Path(__file__).parent

  router = SwaggerRouter(
      search_dirs=[base],
      swagger_ui='/api/',
      default_validate=True,
  )

  router.include('spec1.yaml')
  router.include('spec2.yaml')

  router.add_route('GET', '/status', 'mymod.get_status_coro')
  router.add_route('GET', '/status2', 'mymod.View.get_status_method')
  router.add_route('GET', '/state', get_state_handler)


Handlers
^^^^^^^^

mymod.py contains:

.. code-block:: python

    async def get_status_coro(request):
        return web.Responce(body=b'')

    class View:
        """ Not inherited aiohttp.web.AbstractView
        must implemented simple def __init__(self)
        """
        async def get_status_method(request):
            return web.Responce(body=b'')

        async def create_doc():
            r = self.request  # access to request
            return web.Responce(body=b'')


If you specify parameters in operation and router created with default_validate=True
you can access to valid parameters:

.. code-block:: python

    async def get_status_coro(request, road_id, user_id):
        assert request['road_id'] is road_id
        return web.Responce(body=b'')

If the input is not valid to be generated with the status response 400.
To intercept the validation failure and to prevent the automatic generation of error,
you must add a parameter errors:

.. code-block:: python

    async def get_status_coro(request, road_id, user_id, errors: defaultdict(set)):
        return web.Responce(body=b'')

if the docstring contains the body of the operation is considered to validate the priority:

.. code-block:: python

    async def handler(request, road_id, user_id, errors):
        """
        ---
        parameters:
          - name: road_id
            in: path
            type: integer
          - name: user_id
            in: query
            type: string
        """
        return web.Responce(body=b'')

Use router
^^^^^^^^^^

.. code-block:: python

  Application(router=router)


Swagger-ui
^^^^^^^^^^

If in spec1.yaml basePath specify as /api/1
then swagger-ui for spec1 located on `/api/?spec=/api/1`.
If basePath in spec2 specify as /api/1 then on location `/api/?spec=/api/1` will be mixed spec.
Otherwise swagger-ui located on `basePath`/api/.


More `examples <https://github.com/aamalev/aiohttp_apiset/tree/master/examples>`_
