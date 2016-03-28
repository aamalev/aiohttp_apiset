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
    paths = [url for url, v, n in swagger_router.routes]
    assert '/api/1/file/image' in paths


@pytest.mark.asyncio
async def test_route_include(swagger_router: SwaggerRouter):
    paths = [url for url, v, n in swagger_router.routes]
    assert '/api/1/include2/inc/image' in paths
