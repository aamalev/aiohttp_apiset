aiohttp-apiset
==============

.. image:: https://travis-ci.org/aamalev/aiohttp_apiset.svg?branch=master
  :target: https://travis-ci.org/aamalev/aiohttp_apiset

.. image:: https://codecov.io/gh/aamalev/aiohttp_apiset/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/aamalev/aiohttp_apiset

.. image:: https://img.shields.io/pypi/v/aiohttp_apiset.svg
  :target: https://pypi.python.org/pypi/aiohttp_apiset

.. image:: https://readthedocs.org/projects/aiohttp-apiset/badge/?version=latest
  :target: http://aiohttp-apiset.readthedocs.io/en/latest/?badge=latest
  :alt: Documentation Status

Package to build routes and validate request using swagger specification 2.0.

Features
--------

- Building of the routing from specification swagger
- Using inclusions other specifications with concatenate url
- Optional output of the resulting specification and view embed `swagger-ui <https://github.com/swagger-api/swagger-ui>`_
- Advanced router with TreeResource
- Extract specify parameters from request and validate with jsonschema
- Serialize data as response with middleware

Usecase
-------

Package aiohttp_apiset allows supports several strategies:

- The foreign specification. When the specification
  is made and maintained by another team.
- The specification in the code. When the fragments of specification
  are placed in the docstrings.
- Mixed strategy. When routing are located in the specification files
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
      router = SwaggerRouter(
          swagger_ui='/swagger/',
          version_ui=2,
      )
      router.add_get('/pets/{pet_id}', handler=handler)

      app = web.Application(
          router=router,
          middlewares=[jsonify],
      )

      web.run_app(app)

Is now available in the swagger-ui to the address http://localhost:8080/swagger/.
Available both branch swagger-ui. For use branch 3.x visit http://localhost:8080/swagger/?version=3


Examples: `examples <https://github.com/aamalev/aiohttp_apiset/tree/master/examples>`_
