from aiohttp import web
import pytest


@pytest.mark.asyncio
async def test_init(view, mocker):
    m = mocker.Mock()
    m.method = 'GET'
    m.match_info = {}
    v = view(m)
    assert v._postfixes == ['/{id}', '']


@pytest.mark.parametrize('prefix', [''])
@pytest.mark.asyncio
async def test_get(view, mocker, prefix):
    m = mocker.Mock()
    m.method = 'GET'
    m.path = ''
    m.match_info = {}
    with pytest.raises(web.HTTPOk):
        await view.factory(prefix=prefix)(m)


@pytest.mark.parametrize('prefix', ['/{id}'])
@pytest.mark.asyncio
async def test_retrieve(view, mocker, prefix):
    m = mocker.Mock()
    m.method = 'GET'
    m.path = '/1'
    m.match_info = {}
    with pytest.raises(web.HTTPGone):
        await view.factory(prefix=prefix)(m)
