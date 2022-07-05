from pathlib import Path

from aiohttp import hdrs, web

from aiohttp_apiset import Config, setup
from aiohttp_apiset.config.operation import OperationIdMapping
from aiohttp_apiset.middlewares import CorsConfig, cors, jsonify
from aiohttp_apiset.openapi.loader.v3_1 import Loader
from aiohttp_apiset.validator import ValidationError


BASE = Path(__file__).parent

DB = {}


async def set_document(request, doc_id, payload):
    """ Simple handler for set document
    :param request: aiohttp.web.Request
    :param errors: aiohttp_apiset.exceptions.ValidationError
                   optional param for manual raise validation errors
    :return: dict
    """

    errors = ValidationError()

    if doc_id in DB:
        errors['doc_id'].add('Document already exists')

    if errors:
        raise errors

    payload['doc_id'] = doc_id
    DB[doc_id] = payload

    # dict response for jsonify middleware
    return payload


# operationId-handler association
opmap = OperationIdMapping(
    setDocument=set_document
)


def main():
    loader = Loader()
    loader.add_directory(BASE)
    loader.load('swagger.yaml')
    config = Config(
        loader=loader,
        operation_id_mapping=opmap,
        ui_path='/swagger/',
        ui_version=4
    )
    app = web.Application(middlewares=[
        cors(CorsConfig(allow_headers=[hdrs.AUTHORIZATION])),
        jsonify(),
    ])
    setup(config, app)
    web.run_app(app)


if __name__ == '__main__':
    main()
