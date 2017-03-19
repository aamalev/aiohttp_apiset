aiohttp_apiset
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

Package to build routes and validate request using swagger specification.

Features
--------

- Building of the routing from specification swagger
- Using inclusions other specifications with concatenate url
- Optional output of the resulting specification and view embed swagger-ui
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

Examples: `examples <https://github.com/aamalev/aiohttp_apiset/tree/master/examples>`_
