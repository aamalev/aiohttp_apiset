import asyncio

from aiohttp import web
import pytest


def test_init(view, mocker):
    m = mocker.Mock()
    m.method = 'GET'
    m.match_info = {}
    v = view(m)
    assert v._postfixes == ['/{id}', '']


@pytest.mark.parametrize('prefix', [''])
@asyncio.coroutine
def test_get(view, mocker, prefix):
    m = mocker.Mock()
    m.method = 'GET'
    m.path = ''
    m.match_info = {}
    with pytest.raises(web.HTTPOk):
        yield from view.factory(prefix=prefix)(m)


@pytest.mark.parametrize('prefix', ['/{id}'])
@asyncio.coroutine
def test_retrieve(view, mocker, prefix):
    m = mocker.Mock()
    m.method = 'GET'
    m.path = '/1'
    m.match_info = {}
    with pytest.raises(web.HTTPGone):
        yield from view.factory(prefix=prefix)(m)
