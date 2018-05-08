import json
from pathlib import Path

import pytest
from aiohttp import web, hdrs
from aiohttp.test_utils import make_mocked_request as make_request
from yarl import URL

from aiohttp_apiset.dispatcher import \
    TreeUrlDispatcher, Route, TreeResource, Location, ContentReceiver
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


async def test_simple(dispatcher: TreeUrlDispatcher, request: web.Request):
    request = make_request('GET', '/api/1/pet/1')
    md = await dispatcher.resolve(request)
    assert md == {'id': '1'}

    request = make_request('GET', '/api/1/pets')
    md = await dispatcher.resolve(request)
    assert not md


async def test_multisubs(dispatcher: TreeUrlDispatcher):
    url = '/api/1/host/{host}/eth{num}/{ip:[.\d]+}/'
    dispatcher.add_route('GET', url, handler)

    request = make_request('GET', '/api/1/host/myhost/eth0/127.0.0.1/')
    md = await dispatcher.resolve(request)
    assert len(md)
    assert 'ip' in md
    assert 'num' in md
    assert 'host' in md

    request = make_request('GET', '/api/1/host/myhost/eth0/127.0.0.1')
    md = await dispatcher.resolve(request)
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
])
async def test_import_handler(hstr):
    handler, parameters = Route._import_handler(hstr)
    with pytest.raises(web.HTTPException):
        await handler(**{k: None for k in parameters})


def test_import_one_dot_handler():
    Route._import_handler('asyncio.wait')


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


async def test_static(loop, test_client, mocker):
    f = Path(__file__)
    dispatcher = TreeUrlDispatcher()
    dispatcher.add_static('/static', f.parent, name='static')
    app = web.Application(router=dispatcher, loop=loop)
    client = await test_client(app)

    url = dispatcher['static'].url_for(filename=f.name)
    responce = await client.get(url)
    assert responce.status == 200

    m = mocker.patch('aiohttp_apiset.dispatcher.mimetypes')
    m.guess_type.return_value = None, None
    responce = await client.get(url)
    assert responce.status == 200

    url = dispatcher['static'].url_for(filename='..' + f.name)
    responce = await client.get(url)
    assert responce.status == 403

    url = dispatcher['static'].url_for(filename='1/2/3')
    responce = await client.get(url)
    assert responce.status == 404

    url = dispatcher['static'].url_for(filename='')
    responce = await client.get(url)
    assert responce.status == 404


async def test_static_with_default(loop, test_client):
    f = Path(__file__)
    dispatcher = TreeUrlDispatcher()
    dispatcher.add_static('/static', f.parent, name='static', default=f.name)
    dispatcher.add_static('/static2', f.parent, name='static2', default='1234')
    app = web.Application(router=dispatcher, loop=loop)
    client = await test_client(app)

    url = dispatcher['static'].url_for(filename='1/2/3')
    responce = await client.get(url)
    assert responce.status == 200

    url = dispatcher['static2'].url_for(filename='1/2/3')
    responce = await client.get(url)
    assert responce.status == 404

    url = dispatcher['static'].url_for(filename='')
    responce = await client.get(url)
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
    l = Location(formatter='')
    m, allow = l.resolve(mocker.Mock(), '/not', {})
    assert not m
    assert not allow


def test_novalid_path():
    r = TreeUrlDispatcher()
    with pytest.raises(ValueError):
        r.add_resource('dfsdf')
    with pytest.raises(ValueError):
        r.add_get('dfsdf', None)


async def test_dispatcher_not_resolve():
    r = TreeUrlDispatcher()
    r.add_put('/', handler)
    req = make_request('GET', '/')
    a = await r.resolve(req)
    assert isinstance(a.http_exception, web.HTTPMethodNotAllowed)


async def test_default_options(test_client):
    headers = {
        hdrs.ACCESS_CONTROL_REQUEST_HEADERS: hdrs.AUTHORIZATION}
    request = make_request('OPTIONS', '/', headers=headers)
    router = TreeUrlDispatcher()
    mi = await router.resolve(request)
    assert isinstance(mi, MatchInfoError)

    app = web.Application(router=router)
    router.set_cors(app)
    router.add_get('/', lambda request: web.Response())
    mi = await router.resolve(request)
    assert not isinstance(mi, MatchInfoError)
    client = await test_client(app)
    response = await client.options('/', headers=headers)
    assert response.status == 200
    h = response.headers
    assert h[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] == '*'
    assert h[hdrs.ACCESS_CONTROL_ALLOW_METHODS] == 'GET'
    assert h[hdrs.ACCESS_CONTROL_ALLOW_HEADERS] == hdrs.AUTHORIZATION


async def test_init():
    r = TreeUrlDispatcher()
    r.add_get('/', 'tests.conftest.ViewWithInit.get')
    req = make_request('GET', '/')
    mi = await r.resolve(req)
    result = await mi.handler(req)
    assert result is req, result


async def test_branch_path():
    r = TreeUrlDispatcher()
    h = 'tests.conftest.ViewWithInit.get'
    r.add_get('/net/ip/', h)
    route = r.add_get('/net/{ip}/host', h)
    req = make_request('GET', '/net/ip/host')
    mi = await r.resolve(req)
    assert mi.route is route


async def test_subrouter():
    request = make_request('GET', '/a/b/c/d')
    router = TreeUrlDispatcher()
    subapp = web.Application(router=router)
    route = subapp.router.add_get('/c/d', handler)
    app = web.Application()
    app.add_subapp('/a/b', subapp)
    m = await app.router.resolve(request)
    assert route == m.route


async def test_superrouter():
    request = make_request('GET', '/a/b/c/d')
    router = TreeUrlDispatcher()
    subapp = web.Application()
    route = subapp.router.add_get('/c/d', handler)
    app = web.Application(router=router)
    app.add_subapp('/a/b', subapp)
    m = await app.router.resolve(request)
    assert route == m.route


async def test_content_receiver():
    cr = ContentReceiver()
    l1 = len(cr)
    assert l1
    mime_json = 'application/json'
    assert mime_json in cr
    cr[None] = cr[mime_json]
    assert len(cr) == l1 + 1
    request = make_request('PUT', '/', headers={'Content-Type': mime_json})
    request._read_bytes = json.dumps(2).encode()
    assert 2 == await cr.receive(request)
    del cr[None]

    cr.freeze()
    with pytest.raises(RuntimeError):
        del cr[mime_json]
    with pytest.raises(RuntimeError):
        cr[None] = None

    request = make_request('PUT', '/', headers={'Content-Type': '1'})
    with pytest.raises(TypeError):
        await cr.receive(request)

    assert list(cr)


async def test_set_content_receiver(loop):
    async def test_receiver(request):
        pass

    r = TreeUrlDispatcher()
    r.set_content_receiver('test', test_receiver)
    r.add_post('/', 'tests.conftest.SimpleView.post')
    req = make_request('POST', '/', headers={'Content-Type': 'test'})
    mi = await r.resolve(req)
    assert mi.route._content_receiver.get('test') is test_receiver


async def test_dynamic_sort():
    r = TreeUrlDispatcher()
    r.add_get('/a/{b}-{c}', handler)
    route = r.add_get('/a/{b}-{c}.jpg', handler)
    req = make_request('GET', '/a/2-3.jpg')
    mi = await r.resolve(req)
    assert mi.route is route
