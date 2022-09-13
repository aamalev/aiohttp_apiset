import pytest
from aiohttp import hdrs, web

from aiohttp_apiset import middlewares


ACCESS_CONTROL_HEADERS = [
    hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
    hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
    hdrs.ACCESS_CONTROL_ALLOW_METHODS,
    hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
    hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
    hdrs.ACCESS_CONTROL_MAX_AGE
]

NONE = object()

CONFIG_VARIANTS = [
    middlewares.CorsConfig(
        allow_origin='*',
        allow_credentials=True,
        allow_headers=['Authorization'],
        allow_requested_headers=False,
        allow_methods=['GET', 'HEAD'],
        expose_headers=['X-HMAC-Signature'],
        max_age=60
    ),
    middlewares.CorsConfig(
        allow_origin='https://example.com',
        allow_credentials=False,
        allow_headers=None,
        allow_requested_headers=True,
        allow_methods=[],
        expose_headers=[],
        max_age=None
    ),
    middlewares.CorsConfig(
        allow_origin=['https://example.com', 'https://example.org'],
        allow_credentials=True,
        allow_headers=None,
        allow_requested_headers=False,
        allow_methods=['POST', 'PATCH'],
        expose_headers=None,
        max_age=None
    ),
]


@pytest.mark.parametrize('config', CONFIG_VARIANTS)
async def test_cors(aiohttp_client, config):
    async def handler(request):
        return web.Response(text='OK')

    cors = middlewares.cors(config)
    app = web.Application(middlewares=[cors])
    app.router.add_get('/', handler)
    client = await aiohttp_client(app)

    rep = await client.get('/')
    assert rep.status == 200, await rep.text()

    _assert_no_access_control_headers(rep)

    rep = await client.get('/', headers={hdrs.ORIGIN: 'https://example.com'})
    assert rep.status == 200, await rep.text()
    _validate_base_access_control_headers(rep, config)

    request_headers = {
        hdrs.ORIGIN: 'https://example.com',
        hdrs.ACCESS_CONTROL_REQUEST_METHOD: 'GET'
    }
    if config.allow_requested_headers:
        request_headers[hdrs.ACCESS_CONTROL_REQUEST_HEADERS] = 'Accept,Content-Type'

    rep = await client.options('/', headers=request_headers)
    assert rep.status == 200, await rep.text()
    _validate_base_access_control_headers(rep, config)
    _validate_preflight_access_control_headers(rep, config)


def _assert_no_access_control_headers(rep):
    for i in ACCESS_CONTROL_HEADERS:
        assert i not in rep.headers


def _validate_base_access_control_headers(rep, config):
    if not isinstance(config.allow_origin, list):
        allow_origin = [config.allow_origin]
    else:
        allow_origin = config.allow_origin
    _validate_header(rep, hdrs.ACCESS_CONTROL_ALLOW_ORIGIN, allow_origin)
    _validate_header(rep, hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS, 'true', config.allow_credentials)
    _validate_header(rep, hdrs.ACCESS_CONTROL_EXPOSE_HEADERS, config.expose_headers)


def _validate_preflight_access_control_headers(rep, config):
    if config.allow_headers:
        allow_headers = config.allow_headers
    elif config.allow_requested_headers:
        allow_headers = ['Accept,Content-Type']
    else:
        allow_headers = None
    _validate_header(rep, hdrs.ACCESS_CONTROL_ALLOW_HEADERS, allow_headers)
    _validate_header(rep, hdrs.ACCESS_CONTROL_ALLOW_METHODS, config.allow_methods)
    _validate_header(rep, hdrs.ACCESS_CONTROL_MAX_AGE, str(config.max_age), config.max_age is not None)


def _validate_header(rep, header_name, expected_value, condition=NONE):
    if condition is NONE:
        has_value = bool(expected_value)
    else:
        has_value = condition
    if has_value:
        if isinstance(expected_value, list):
            actual_value = rep.headers.getall(header_name)
        else:
            actual_value = rep.headers.get(header_name)
        assert actual_value == expected_value
    else:
        assert header_name not in rep.headers
