=======
History
=======

0.9.12 (2020-11-01)
-------------------

* up swagger-ui to 3.36.1


0.9.11 (2020-08-16)
-------------------

* Support add_routes


0.9.10 (2020-03-08)
-------------------

* True YamlSerializer for schema


0.9.9 (2020-01-31)
------------------

* Cache for yaml_load
* up swagger-ui to 3.25.0


0.9.8 (2019-11-09)
------------------

* up aiohttp ot 3.6.X
* up swagger-ui to 3.24.2


0.9.7 (2019-07-31)
------------------

* fix warning yaml
* up swagger-ui to 3.23.3


0.9.6 (2019-03-10)
------------------

* fix static access dir
* support aiohttp 3.5
* up swagger-ui to 3.21.0


0.9.5 (2018-12-12)
------------------

* fix safe static


0.9.4 (2018-08-09)
------------------

* replace scheme to X-Forwarded-Proto for spec_url
* up swagger-ui to 3.18.0


0.9.3 (2018-07-26)
------------------

* Fix copy from schema loader
* Default check_schema in Validator
* support aiohttp 3.3
* up swagger-ui to 3.17.5


0.9.2 (2018-07-04)
------------------

* Add spec_url param to SwaggerRouter
* up swagger-ui to 3.17.2


0.9.1 (2018-05-08)
------------------

* fix sort of dynamic locations
* middleware binary
* support aiohttp 3.2
* up swagger-ui to 3.14.1


0.9 (2018-03-26)
----------------

* Support $ref in docstrings
* Added ContentReceiver
* Drop support py34
* Renamed SubLocation to Location



0.8.1 (2018-02-25)
------------------

* Support parameters in PathItem


0.8.0 (2018-02-22)
------------------

* Support aiohttp 3.0.1
* Support subapp
* UrlTreeDispatcher.resources now return resources only
* Default_operation & setdefault responses
* Up swagger-ui to 3.10.0
* Await Future in jsonify



0.7.4 (2017-12-22)
------------------

* Support aiohttp 2.3.6
* Up swagger-ui to 3.7.0


0.7.3 (2017-11-01)
------------------

* Support OrderedDict in loader with yaml tag merge


0.7.2 (2017-10-31)
------------------

* Fix ValidationError constructor
* Modify Errors instance through the attribute


0.7.1 (2017-10-31)
------------------

* Keep the order of the URLs from the specification
* More error content in the response
* swagger-ui up to 3.4.1


0.7.0 (2017-10-23)
------------------

* Introduced Errors and ValidationError
* Access to original spec by name
* Now the default_validate is True
* Added param headers to set_cors for specify default headers
* swagger-ui up to 3.4.0



0.6.2 (2017-08-29)
------------------

* Loader support encoding
* Absolute url in ui
* swagger-ui up to 3.1.7


0.6.1 (2017-08-26)
------------------

* Method set_cors


0.6 (2017-08-25)
----------------

* New loader for load schemas
* Customization format_checkers for check and convert value
* Support swagger-ui version 2 & 3
* Fixed resolve route and middleware
* Optional coromethod init in cbv



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
