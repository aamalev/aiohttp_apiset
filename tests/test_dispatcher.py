import asyncio

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request as make_request
from yarl import URL

from aiohttp_apiset.dispatcher import TreeUrlDispatcher, Route
from aiohttp_apiset.compat import MatchInfoError


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
    location = dispatcher['pet']
    assert location.url(parts={'id': 1}) == '/api/1/pet/1'
    assert location.url_for(id=1) == URL('/api/1/pet/1')
    assert repr(location)

    route = location._routes['GET']
    assert route.url(parts={'id': 1}) == '/api/1/pet/1'
    assert route.url_for(id=1) == URL('/api/1/pet/1')
    assert repr(route)
    assert route.name
    assert route.get_info() is not None

    assert dispatcher.tree_resource.url_for() == URL('/')
    assert dispatcher.tree_resource.url(query={'q': 1}) == '/?q=1'
    assert repr(dispatcher.tree_resource)
    assert dispatcher.tree_resource.get_info() is not None


@pytest.mark.parametrize('hstr', [
    'tests.conftest.View.retrieve',
    'tests.conftest.SimpleView.get',
    'tests.conftest.SimpleView.post',
    'asyncio.wait',  # cover one dot str handler
])
def test_import_handler(hstr):
    handler, parameters = Route._import_handler(hstr)
    handler(**{k: None for k in parameters})
