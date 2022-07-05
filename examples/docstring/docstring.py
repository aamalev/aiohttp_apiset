from pathlib import Path

from aiohttp import web

from aiohttp_apiset import Config, setup
from aiohttp_apiset.middlewares import jsonify
from aiohttp_apiset.openapi.loader.v2_0 import Loader
from aiohttp_apiset.validator import ValidationError


BASE = Path(__file__).parent


DB = {}


async def set_document(request, doc_id, body):
    """ Simple handler for set document
    ---
    tags: [documents]
    description: Set document
    parameters:
      - name: doc_id
        in: path
        type: integer
        minimum: 0
      - name: body
        in: body
        schema:
          type: object
          additionalProperties: false
          properties:
            a:
              type: integer
              minimum: 0
    responses:
      200:
        description: OK
      400:
        description: Validation error
    """
    errors = ValidationError()

    if doc_id in DB:
        errors['doc_id'].add('Document already exists')

    if errors:
        raise errors

    body['doc_id'] = doc_id
    DB[doc_id] = body

    # dict response for jsonify middleware
    return body


def main():
    loader = Loader.default()
    config = Config(loader, ui_path='/swagger/', ui_version=3)
    config.add_operation('POST', r'/doc/{doc_id:\d+}', set_document)
    app = web.Application(middlewares=[jsonify()])
    setup(config, app)
    # is now available in the swagger-ui to the address http://localhost:8080/swagger/
    web.run_app(app)


if __name__ == '__main__':
    main()
