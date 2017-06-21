=======
History
=======

0.5.2 (2017-06-21)
------------------

* Add method Jsonify.resolve_exception
* Add class Validator with method factory


0.5.1 (2017-06-20)
------------------

* Param default_options_handler
* Refactoring middleware jsonify
* Now require aiohttp>=1.2


0.5.0 (2017-06-16)
------------------

* fix naming SubLocation
* add to Sublocation add_route
* swagger-ui.min.js as default instead swagger-ui.js
* default tag 'default' instead 'without swagger'
* kwargs as parts in sublocation.url


0.4.5 (2017-05-27)
------------------

* Default show single spec in ui
* URL filtering for generated specifications by spec param

0.4.4 (2017-05-26)
------------------

* Fix swagger-ui prefix

0.4.3 (2017-05-26)
------------------

* Use default value for array when collectionFormat is brackets or multi (#9)
* Back swagger-ui to 2.x

0.4.2 (2017-04-28)
------------------

* Up swagger-ui and fix prefix static url
* Support for decimal in JsonEncoder

0.4.1 (2017-03-26)
------------------

* Added check for similar patterns on one location
* Fix static return default if filename empty

0.4.0 (2017-03-22)
------------------

* TreeUrlDispatcher is stand-alone router
* swagger_ui param now str url location for swagger-ui
* spec query param for swagger-ui location to point to basePath
* Take into account the default value for array parameters (Alain Leufroy #6)
* Extract docstring swagger data in route_factory
* Compatibility with py36 and aiohttp2.0

0.3.4 (2016-12-20)
------------------

* fixed swagger extractor from docstring
* support aiohttp 1.2

0.3.3 (2016-12-16)
------------------

* Added support pathlib
* Drop deprecated methods in views

0.3.2 (2016-12-14)
------------------

* Added support for collectionFormat (#4)

0.3.1 (2016-11-25)
------------------

* fix zero for number parameter
* transfer validation errors into client handler if specified argument errors

0.3.0 (2016-11-24)
------------------

* Added class OperationIdMapping and param operationId_mapping in SwaggerRouter.include
  for load authentic specification with specify operationId (#2)
* Fixed validation form with file
* Fixed overriding basePath
* Added jinja2 decorator for working with aiohttp_jinja2
* Loading operation body from docstring
* Blank string param for number and integer treated as a missed

0.2.5 (2016-11-08)
------------------

* Fixed verbosity errors
* Set default value from swagger operationObject
* Started docs on http://aiohttp-apiset.readthedocs.io
* Swagger-ui index on `basePath`/apidoc/

0.2.4 (2016-11-06)
------------------

* Added verbosity errors validate with jsonschema

0.2.3 (2016-11-05)
------------------

* Added compatibility with aiohttp >= 1.1
* Added safe decode form and json
* Fixed extract body

0.2.2 (2016-10-28)
------------------

* Fixed convertation from match_info

0.2.1 (2016-10-27)
------------------

* Output conversion parameter errors in response
* Fix validation

0.2.0 (2016-10-26)
------------------

0.1.13 (2016-05-02)
-------------------
