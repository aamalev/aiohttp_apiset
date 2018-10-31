from collections import OrderedDict
from pathlib import Path

import pytest

from aiohttp_apiset.swagger.loader import (AllOf, DictLoader,
                                           ExtendedSchemaFile, FileLoader,
                                           Loader, SchemaFile, yaml)


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
    f = ExtendedSchemaFile(p, dirs=[d, d / 'data'])
    paths = f['paths']
    items = list(paths.items())
    assert len(items) == len([url for url in paths])
    for url, m in items:
        methods = paths[url]
        assert m == methods


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
    loader_instance = loader()
    d = Path(__file__).parent
    loader_instance.add_search_dir(d)
    loader_instance.add_search_dir(d / 'data')
    assert loader_instance.load(p)


@pytest.mark.parametrize('loader', [
    FileLoader,
    DictLoader,
])
@pytest.mark.parametrize('p', [
    'data/schema01.yaml',
    'data/root.yaml',
])
def test_loader_resolve_data(loader, p):
    loader_instance = loader()
    d = Path(__file__).parent
    loader_instance.add_search_dir(d)
    assert '/api/1' == loader_instance(p + '#/basePath')
    data = loader_instance.resolve_data({'$ref': p + '#/basePath'})
    assert '/api/1' == data, data
    data = loader_instance.resolve_data({'t': {'$ref': p + '#/definitions/g'}})
    assert {'t': {'f': 1, 'd': 2}} == data, data


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


def test_local_refs():
    class F(dict):
        local_refs = {('x', 'y'): {'z': 3}}
    f = F(x={'w': 1}, r=4)
    loader = FileLoader()
    assert loader._set_local_refs(f) == {'x': {'y': {'z': 3}, 'w': 1}, 'r': 4}


def test_load_local_refs(swagger_router):
    loader = swagger_router._file_loader
    result = loader.load('data/root.yaml')
    assert 'data/include.yaml' in FileLoader.files
    assert FileLoader.local_refs
    assert ExtendedSchemaFile.files
    assert 'Defi' in result['definitions']
