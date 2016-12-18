from pathlib import Path

from aiohttp import web
from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset.middlewares import jsonify
from aiohttp_apiset.swagger.operations import OperationIdMapping


BASE = Path(__file__).parent


def set_document(request):
    """ Simple handler for set document
    :param request: aiohttp.web.Request
    :return: dict
    """

    # check validation
    assert 'id' in request
    assert isinstance(request['id'], int)
    assert request['id'] <= 0
    assert 'body' in request
    assert isinstance(request['body'], dict)
    assert request['body']['a'] > 0

    # dict response for jsonify middleware
    return dict(request)


# operationId-handler association
opmap = OperationIdMapping(
    setDocument=set_document
)


def main():
    router = SwaggerRouter(
        encoding='utf-8',
        default_validate=True,
        swagger_ui=True,
        search_dirs=[BASE],
    )

    app = web.Application(
        router=router,
        middlewares=[jsonify],
    )

    # Include our specifications in a router,
    # is now available in the swagger-ui to the address /apidoc/
    router.include(
        spec='swagger.yaml',
        operationId_mapping=opmap,
    )

    web.run_app(app)


if __name__ == '__main__':
    main()
