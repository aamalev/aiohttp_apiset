from pathlib import Path

from aiohttp import web
from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset.middlewares import jsonify


BASE = Path(__file__).parent


DB = {}


def set_document(request, doc_id, body, errors):
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
    if doc_id in DB:
        errors['doc_id'].add('Document already exists')

    if errors:
        raise errors

    body['doc_id'] = doc_id
    DB[doc_id] = body

    # dict response for jsonify middleware
    return body


def main():
    router = SwaggerRouter(
        swagger_ui='/swagger/',
    )
    router.add_post('/doc/{doc_id:\d+}', handler=set_document)

    app = web.Application(
        router=router,
        middlewares=[jsonify],
    )

    # is now available in the swagger-ui to the address http://localhost:8080/swagger/
    web.run_app(app)


if __name__ == '__main__':
    main()
