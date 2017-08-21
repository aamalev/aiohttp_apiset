import asyncio
from pathlib import Path

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request as make_request
from yarl import URL

from aiohttp_apiset.dispatcher import \
    TreeUrlDispatcher, Route, TreeResource, SubLocation
from aiohttp_apiset.compat import MatchInfoError


def handler(request):
    return web.HTTPOk()


@pytest.fixture
def dispatcher():
    d = TreeUrlDispatcher()
    location = d.add_resource('/', name='root')
    location.add_route('GET', handler)
    d.add_route('GET', '/api/', handler)
    d.add_route('GET', '/api', handler)
    d.add_route('*', '/api/1/pets', handler)
    d.add_route('GET', '/api/1/pet/{id}', handler, name='pet')
    d.add_route('GET', '/api/1/pet/{id}/', handler)
    return d


def test_create(dispatcher: TreeUrlDispatcher):
    assert dispatcher.tree_resource._location._subs


def test_add_resource(dispatcher: TreeUrlDispatcher):
    location = dispatcher.add_resource('/api/1/dogs', name='dogs')
    assert str(location.url_for()) == '/api/1/dogs'


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
    location = dispatcher['root']
    assert 'path' in location.get_info()
    route = location._routes['GET']
    route.set_info(l=1)
    assert route.get_info().get('l') == 1

    location = dispatcher['pet']
    assert location.url(parts={'id': 1}) == '/api/1/pet/1'
    assert location.url_for(id=1) == URL('/api/1/pet/1')
    assert repr(location)

    route = location._routes['GET']
    assert route.url(parts={'id': 1}) == '/api/1/pet/1'
    assert route.url_for(id=1) == URL('/api/1/pet/1')
    assert repr(route)
    assert route.name
    assert 'formatter' in route.get_info()

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


def test_import_handler_():
    with pytest.raises(ValueError):
        Route._import_handler('a')
    assert Route._import_handler('aiohttp.web.View.get')


def test_view_locations(dispatcher: TreeUrlDispatcher):
    resources = dispatcher.resources()
    assert list(resources)[0] in resources
    assert len(resources)
    routes = dispatcher.routes()
    assert list(routes)[0] in routes
    assert len(routes)


@asyncio.coroutine
def test_static(loop, test_client, mocker):
    f = Path(__file__)
    dispatcher = TreeUrlDispatcher()
    dispatcher.add_static('/static', f.parent, name='static')
    app = web.Application(router=dispatcher, loop=loop)
    client = yield from test_client(app)

    url = dispatcher['static'].url_for(filename=f.name)
    responce = yield from client.get(url)
    assert responce.status == 200

    m = mocker.patch('aiohttp_apiset.dispatcher.mimetypes')
    m.guess_type.return_value = None, None
    responce = yield from client.get(url)
    assert responce.status == 200

    url = dispatcher['static'].url_for(filename='..' + f.name)
    responce = yield from client.get(url)
    assert responce.status == 403

    url = dispatcher['static'].url_for(filename='1/2/3')
    responce = yield from client.get(url)
    assert responce.status == 404

    url = dispatcher['static'].url_for(filename='')
    responce = yield from client.get(url)
    assert responce.status == 404


@asyncio.coroutine
def test_static_with_default(loop, test_client):
    f = Path(__file__)
    dispatcher = TreeUrlDispatcher()
    dispatcher.add_static('/static', f.parent, name='static', default=f.name)
    dispatcher.add_static('/static2', f.parent, name='static2', default='1234')
    app = web.Application(router=dispatcher, loop=loop)
    client = yield from test_client(app)

    url = dispatcher['static'].url_for(filename='1/2/3')
    responce = yield from client.get(url)
    assert responce.status == 200

    url = dispatcher['static2'].url_for(filename='1/2/3')
    responce = yield from client.get(url)
    assert responce.status == 404

    url = dispatcher['static'].url_for(filename='')
    responce = yield from client.get(url)
    assert responce.status == 200


def test_similar_patterns():
    dispatcher = TreeUrlDispatcher()
    dispatcher.add_get('/{a}', handler)
    with pytest.raises(ValueError):
        dispatcher.add_get('/{b}', handler)


def test_treeresource():
    a = TreeResource()
    assert not len(a)
    assert not list(a)


def test_sublocation_notresolved(mocker):
    l = SubLocation(formatter='')
    m, allow = l.resolve(mocker.Mock(), '/not', {})
    assert not m
    assert not allow


def test_novalid_path():
    r = TreeUrlDispatcher()
    with pytest.raises(ValueError):
        r.add_resource('dfsdf')
    with pytest.raises(ValueError):
        r.add_get('dfsdf', None)


@asyncio.coroutine
def test_dispatcher_not_resolve():
    r = TreeUrlDispatcher()
    r.add_put('/', handler)
    req = make_request('GET', '/')
    a = yield from r.resolve(req)
    assert isinstance(a.http_exception, web.HTTPMethodNotAllowed)


@asyncio.coroutine
def test_default_options(test_client):
    request = make_request('OPTIONS', '/')
    router = TreeUrlDispatcher(default_options_handler=True)
    router.add_get('/', lambda request: web.Response())
    mi = yield from router.resolve(request)
    assert not isinstance(mi, MatchInfoError)
    app = web.Application(router=router)
    client = yield from test_client(app)
    response = yield from client.options('/')
    assert response.status == 200

    router = TreeUrlDispatcher(default_options_handler=None)
    mi = yield from router.resolve(request)
    assert isinstance(mi, MatchInfoError)


@asyncio.coroutine
def test_init():
    r = TreeUrlDispatcher()
    r.add_get('/', 'tests.conftest.ViewWithInit.get')
    req = make_request('GET', '/')
    mi = yield from r.resolve(req)
    result = yield from mi.handler(req)
    assert result is req, result
