import asyncio

import pytest
from aiohttp import web
from aiohttp.web_urldispatcher import MatchInfoError
from aiohttp.test_utils import make_mocked_request as make_request

from aiohttp_apiset.dispatcher import TreeUrlDispatcher, Route


def handler(request):
    return web.HTTPOk()


@pytest.fixture
def dispatcher():
    d = TreeUrlDispatcher()
    d.add_route('GET', '/', handler)
    d.add_route('GET', '/api/', handler)
    d.add_route('GET', '/api', handler)
    d.add_route('*', '/api/1/pets', handler)
    d.add_route('GET', '/api/1/pet/{id}', handler, name='pet')
    d.add_route('GET', '/api/1/pet/{id}/', handler)
    return d


def test_create(dispatcher: TreeUrlDispatcher):
    assert dispatcher.tree_resource._location._subs


@asyncio.coroutine
def test_simple(dispatcher: TreeUrlDispatcher, request: web.Request):
    request = make_request('GET', '/api/1/pet/1')
    md = yield from dispatcher.resolve(request)
    assert md == {'id': '1'}

    request = make_request('GET', '/api/1/pets')
    md = yield from dispatcher.resolve(request)
    assert not md


@asyncio.coroutine
def test_multisubs(dispatcher: TreeUrlDispatcher):
    url = '/api/1/host/{host}/eth{num}/{ip:[.\d]+}/'
    dispatcher.add_route('GET', url, handler)

    request = make_request('GET', '/api/1/host/myhost/eth0/127.0.0.1/')
    md = yield from dispatcher.resolve(request)
    assert len(md)
    assert 'ip' in md
    assert 'num' in md
    assert 'host' in md

    request = make_request('GET', '/api/1/host/myhost/eth0/127.0.0.1')
    md = yield from dispatcher.resolve(request)
    assert isinstance(md, MatchInfoError)


def test_url(dispatcher: TreeUrlDispatcher):
    assert dispatcher['pet'].url(parts={'id': 1}) == '/api/1/pet/1'


@pytest.mark.parametrize('hstr', [
    'tests.conftest.View.retrieve',
    'tests.conftest.SimpleView.get',
    'tests.conftest.SimpleView.post',
])
def test_import_handler(hstr):
    handler, parameters = Route._import_handler(hstr)
    handler(**{k: None for k in parameters})
