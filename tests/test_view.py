from aiohttp import web
import pytest


@pytest.mark.parametrize('prefix', [''])
async def test_get(view, mocker, prefix):
    m = mocker.Mock()
    m.method = 'GET'
    m.path = ''
    m.match_info = {}
    with pytest.raises(web.HTTPOk):
        await view.factory(prefix=prefix)().get()


@pytest.mark.parametrize('prefix', ['/{id}'])
async def test_retrieve(view, mocker, prefix):
    m = mocker.Mock()
    m.method = 'POST'
    m.path = '/1'
    m.match_info = {}
    with pytest.raises(web.HTTPGone):
        await view.factory(prefix=prefix)().retrieve(m)
