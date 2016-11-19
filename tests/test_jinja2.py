import asyncio
import random

import pytest

from aiohttp_apiset.jinja2 import template


@template('fake.html')
def handler(request):
    return {'req': request}


@template('fake.html')
@asyncio.coroutine
def handler2(request):
    return {'req': request}


@pytest.mark.parametrize('handler', [
    handler, handler2
])
@asyncio.coroutine
def test_simple(swagger_router, handler, mocker):
    route = swagger_router.add_route(
        'GET', '/jinja2/handler{}'.format(random.randrange(0, 999)), handler)
    m = mocker.patch('aiohttp_apiset.jinja2.render_template')
    response = yield from route.handler('request')
    assert response is m()


@template('fake.html')
def handler_():
    return {}


@asyncio.coroutine
def test_simple(swagger_router, mocker):
    route = swagger_router.add_route(
        'GET', '/jinja2/handler{}'.format(random.randrange(0, 999)), handler_)
    m = mocker.patch('aiohttp_apiset.jinja2.render_template')
    response = yield from route.handler()
    assert response is m()
