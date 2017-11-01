from collections import OrderedDict
from pathlib import Path

import pytest

from aiohttp_apiset.swagger.loader import ExtendedSchemaFile, SchemaFile
from aiohttp_apiset.swagger.loader import DictLoader, FileLoader, AllOf
from aiohttp_apiset.swagger.loader import yaml, Loader


def test_load():
    p = Path(__file__).parent / 'data/schema01.yaml'
    f = SchemaFile(p)
    assert f is SchemaFile(p)
    assert f('../data/file.yaml#/basePath') == '/image'
    assert 'get' in f['paths']['/pet']


@pytest.mark.parametrize('p', [
    'data/schema01.yaml',
    'data/root.yaml',
])
def test_paths(p):
    d = Path(__file__).parent
    f = ExtendedSchemaFile(p, [d, d / 'data'])
    paths = f['paths']
    items = list(paths.items())
    assert len(items) == len([url for url in paths])
    for url, m in items:
        methods = paths[url]
        assert dict(m) == dict(methods)  # , pytest.set_trace()


@pytest.mark.parametrize('p', [
    'data/schema01.yaml',
    'data/root.yaml',
])
def test_resolve(p):
    d = Path(__file__).parent
    f = ExtendedSchemaFile(p, [d, d / 'data'])
    data = f.resolve()
    assert data['paths']


def test_route_include(swagger_router):
    paths = [route.url_for().human_repr()
             for route in swagger_router.routes()]
    assert '/api/1/include2/inc/image' in paths, paths


@pytest.mark.parametrize('loader', [
    FileLoader,
    DictLoader,
])
@pytest.mark.parametrize('p', [
    'data/schema01.yaml',
    'data/root.yaml',
])
def test_loader(loader, p):
    l = loader()
    d = Path(__file__).parent
    l.add_search_dir(d)
    l.add_search_dir(d / 'data')
    assert l.load(p)


def test_allOf():
    a = AllOf({'a': 1}, {'b': 2})
    assert dict(a) == {'a': 1, 'b': 2}
    with pytest.raises(KeyError):
        print(a['c'])
    assert len(a) == 2


def test_ordered_with_merge():
    d = """
        d: 1
        a: 2
        c: &c
          f: 3
          j: 4
        t:
          <<: *c
          z: 5
        """
    data = yaml.load(d, Loader)
    assert isinstance(data, OrderedDict)
