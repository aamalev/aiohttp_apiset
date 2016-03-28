from aiohttp import web
import pytest


@pytest.mark.asyncio
async def test_init(view, mocker):
    m = mocker.Mock()
    m.method = 'GET'
    m.match_info = {}
    v = view(m)
    assert v._postfixes == ['/{id}', '']


@pytest.mark.parametrize('prefix', ['', None])
@pytest.mark.asyncio
async def test_get(view, mocker, prefix):
    m = mocker.Mock()
    m.method = 'GET'
    m.path = ''
    m.match_info = {}
    with pytest.raises(web.HTTPOk):
        await view(m, prefix=prefix)


@pytest.mark.parametrize('prefix', ['', None])
@pytest.mark.asyncio
async def test_retrieve(view, mocker, prefix):
    m = mocker.Mock()
    m.method = 'GET'
    m.path = '/{id}'
    m.match_info = {}
    with pytest.raises(web.HTTPGone):
        await view(m, prefix=prefix)
