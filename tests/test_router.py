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
    assert '/file/image' in paths
