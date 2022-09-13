aiohttp-apiset
==============

.. image:: https://github.com/aamalev/aiohttp_apiset/workflows/Tests/badge.svg
  :target: https://github.com/aamalev/aiohttp_apiset/actions?query=workflow%3ATests

.. image:: https://codecov.io/gh/aamalev/aiohttp_apiset/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/aamalev/aiohttp_apiset

.. image:: https://img.shields.io/pypi/v/aiohttp_apiset.svg
  :target: https://pypi.python.org/pypi/aiohttp_apiset

.. image:: https://readthedocs.org/projects/aiohttp-apiset/badge/?version=latest
  :target: http://aiohttp-apiset.readthedocs.io/en/latest/?badge=latest
  :alt: Documentation Status

.. image:: https://img.shields.io/pypi/pyversions/aiohttp_apiset.svg
  :target: https://pypi.python.org/pypi/aiohttp_apiset

Package to build routes and validate request using Swagger 2.0/OpenAPI 3.1.

Features
--------

- Building of the routing from OpenAPI specification
- Include multiple specification files with URL path concatenation
- Optional output of the resulting specification and view embed `Swagger UI <https://github.com/swagger-api/swagger-ui>`_
- Extracting specified parameters from request and validating them with jsonschema
- Serializing response data with middlewares
- CORS support

Usecase
-------

Package aiohttp_apiset allows supports several strategies:

- The foreign specification. When the specification
  is made and maintained by another team.
- The specification in the code. When the fragments of specification
  are placed in the docstrings.
- Mixed strategy. When routes are located in the specification files
  and operations are described in the docstrings.

Example
-------

.. code-block:: python

  async def handler(request, pet_id):
      """
      ---
      tags: [Pet]
      description: Info about pet
      parameters:
        - name: pet_id
          in: path
          type: integer
          minimum: 0
      responses:
        200:
          description: OK
        400:
          description: Validation error
        404:
          description: Not found
      """
      pet = await db.pets.find(pet_id)

      if not pet:
          return {'status': 404, 'msg': 'Not Found'}

      return {
          'pet': pet,  # dict serialized inside jsonify
      }


  def main():
      loader = Loader.default()
      config = Config(loader, ui_path='/swagger/', ui_version=3)
      config.add_operation('GET', r'/pets/{pet_id:\d+}', handler)
      app = web.Application(middlewares=[jsonify()])
      setup(config, app)
      web.run_app(app)

Swagger UI is now available on http://localhost:8080/swagger/.
Supported Swagger UI versions: 2, 3 and 4.
To see another UI version visit ```http://localhost:8080/swagger/?version=<version>```
where ```<version>``` is one of supported versions (2, 3, 4).


See `examples <https://github.com/aamalev/aiohttp_apiset/tree/master/examples>`_ directory for more information.
