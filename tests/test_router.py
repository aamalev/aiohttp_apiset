import pytest

from aiohttp_apiset.routes import SwaggerRouter


@pytest.mark.asyncio
async def test_setup(app):
    SwaggerRouter(
        'data/root.yaml',
        search_dirs=['tests']
    ).setup(app)


@pytest.mark.asyncio
async def test_routes(swagger_router: SwaggerRouter):
    paths = [url for method, url, handler in swagger_router._routes.values()]
    assert '/api/1/file/image' in paths


@pytest.mark.asyncio
async def test_route_include(swagger_router: SwaggerRouter):
    paths = [url for method, url, handler in swagger_router._routes.values()]
    assert '/api/1/include2/inc/image' in paths


def test_route_swagger_include(swagger_router: SwaggerRouter):
    paths = swagger_router._swagger_data['paths']
    assert '/include/image' in paths


def test_route_swagger_view(swagger_router: SwaggerRouter):
    paths = swagger_router._swagger_data['paths']
    assert '/file/image' in paths


@pytest.mark.asyncio
async def test_handler(swagger_router: SwaggerRouter):
    paths = [(r.method, r.url) for r in swagger_router._routes.values()]
    assert ('GET', '/api/1/include/image') in paths


def test_definitions(swagger_router: SwaggerRouter):
    d = swagger_router._swagger_data['definitions']
    assert 'File' in d
    assert 'Defi' in d
