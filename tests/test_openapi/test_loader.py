import pytest

from aiohttp_apiset.openapi.loader.base import ExportFormat
from aiohttp_apiset.openapi.loader.v2_0 import Loader as LoaderV2
from aiohttp_apiset.openapi.loader.v3_1 import Loader as LoaderV3
from aiohttp_apiset.openapi.schema import v2_0 as schema_v2
from aiohttp_apiset.openapi.schema import v3_1 as schema_v3


def test_v2_0(data_root):
    root = data_root / 'openapi/v2_0/examples'
    for i in root.iterdir():
        loader = LoaderV2()
        loader.add_directory(root)
        loader.load(i)
        assert loader.specification.swagger == '2.0'


def test_v3_1(data_root):
    root = data_root / 'openapi/v3_1/examples'
    for i in root.iterdir():
        loader = LoaderV3()
        loader.add_directory(str(root))
        loader.load(i)
        assert loader.specification.openapi == '3.1.0'


@pytest.mark.parametrize('loader_cls', [LoaderV2, LoaderV3])
def test_no_such_directory(data_root, loader_cls):
    loader = loader_cls()
    with pytest.raises(ValueError, match='No such directory'):
        loader.add_directory(data_root / 'no-such-directory')


@pytest.mark.parametrize('version,loader_cls', [('v2_0', LoaderV2), ('v3_1', LoaderV3)])
def test_already_loaded(data_root, version, loader_cls):
    loader = loader_cls()
    loader.add_directory(data_root / 'openapi' / version / 'examples')
    loader.load('petstore.json')
    with pytest.raises(RuntimeError, match='Specification already loaded'):
        loader.load('petstore.json')


@pytest.mark.parametrize('loader_cls', [LoaderV2, LoaderV3])
def test_file_not_found(data_root, loader_cls):
    loader = loader_cls()
    with pytest.raises(FileNotFoundError, match='No such file'):
        loader.load('petstore.json')


@pytest.mark.parametrize('version,loader_cls', [('v2_0', LoaderV2), ('v3_1', LoaderV3)])
def test_dump(data_root, version, loader_cls):
    loader = loader_cls()

    with pytest.raises(RuntimeError, match='Specification is not loaded'):
        loader.dump()

    loader.add_directory(data_root / 'openapi' / version / 'examples')
    loader.load('petstore.json')
    for export_format in [ExportFormat.json, ExportFormat.yaml]:
        loader.dump(export_format=export_format)
        loader.dump(filename='petstore.json', export_format=export_format)


def test_resolve_ref_v2_0(data_root):
    loader = LoaderV2()
    loader.add_directory(data_root / 'openapi/v2_0/examples')

    with pytest.raises(RuntimeError, match='Specification is not loaded'):
        loader.resolve_ref(schema_v2.Schema, '#/definitions/Pet')

    loader.load('petstore.json')
    obj = loader.resolve_ref(schema_v2.Schema, '#definitions/Pet')
    assert isinstance(obj, schema_v2.Schema)
    assert obj.properties['name'].type_ == 'string'

    obj = loader.resolve_ref(schema_v2.Schema, 'petstore.json#definitions/Pet')
    assert isinstance(obj, schema_v2.Schema)

    with pytest.raises(ValueError, match='Reference not found'):
        loader.resolve_ref(schema_v2.Schema, 'no-such-file.json#definitions/Pet')

    with pytest.raises(KeyError, match='Reference not exists'):
        loader.resolve_ref(schema_v2.Schema, '#/definitions/NoSuchRef')

    with pytest.raises(ValueError, match='Reference points to root object'):
        loader.resolve_ref(schema_v2.Schema, '#/')


def test_resolve_ref_v3_1(data_root):
    loader = LoaderV3()
    loader.add_directory(data_root / 'openapi/v3_1/examples')

    with pytest.raises(RuntimeError, match='Specification is not loaded'):
        loader.resolve_ref(schema_v2.Schema, '#/components/schemas/Pet')

    loader.load('petstore.json')
    obj = loader.resolve_ref(schema_v3.Schema, '#components/schemas/Pet')
    assert isinstance(obj, schema_v3.Schema)
    assert obj.properties['name'].type_ == 'string'

    obj = loader.resolve_ref(schema_v2.Schema, 'petstore.json#components/schemas/Pet')
    assert isinstance(obj, schema_v2.Schema)

    with pytest.raises(ValueError, match='Reference not found'):
        loader.resolve_ref(schema_v2.Schema, 'no-such-file.json#components/schemas/Pet')

    with pytest.raises(KeyError, match='Reference not exists'):
        loader.resolve_ref(schema_v2.Schema, '#/components/schemas/NoSuchRef')

    with pytest.raises(KeyError, match='Reference not exists'):
        loader.resolve_ref(schema_v2.Schema, '#/components/NoSuchReference')

    with pytest.raises(ValueError, match='Reference points to root object'):
        loader.resolve_ref(schema_v2.Schema, '#/')


@pytest.mark.parametrize('version,loader_cls', [('v2_0', LoaderV2), ('v3_1', LoaderV3)])
def test_include_paths(data_root, version, loader_cls):
    loader = loader_cls()
    loader.add_directory(data_root / 'openapi' / version / 'include-paths')
    loader.load('root.yaml')
    assert loader.specification.paths


@pytest.mark.parametrize('version,loader_cls', [('v2_0', LoaderV2), ('v3_1', LoaderV3)])
def test_invalid_path_type(data_root, version, loader_cls):
    loader = loader_cls()
    loader.add_directory(data_root / 'openapi' / version)

    with pytest.raises(TypeError, match=r'Expects mapping'):
        loader.load('invalid-paths.yaml')

    with pytest.raises(TypeError, match=r'Unknown path item type'):
        loader.load('invalid-path-type.yaml')


@pytest.mark.parametrize('version,loader_cls', [('v2_0', LoaderV2), ('v3_1', LoaderV3)])
def test_empty_paths_ok(data_root, version, loader_cls):
    loader = loader_cls()
    loader.add_directory(data_root / 'openapi' / version)
    loader.load('empty-paths.yaml')
    assert len(loader.specification.paths) == 0


@pytest.mark.parametrize('version,loader_cls', [('v2_0', LoaderV2), ('v3_1', LoaderV3)])
def test_unknown_file_format(data_root, version, loader_cls):
    loader = loader_cls()
    loader.add_directory(data_root / 'openapi' / version)
    with pytest.raises(ValueError, match=r'Unknown file format: .+\.txt'):
        loader.load('example.txt')


@pytest.mark.parametrize('version,loader_cls', [('v2_0', LoaderV2), ('v3_1', LoaderV3)])
def test_add_operation(data_root, version, loader_cls):
    loader = loader_cls()
    loader.add_directory(data_root / 'openapi' / version)

    if version == 'v2_0':
        operation_data = {
            'operation_id': 'example',
            'responses': {
                '200': {'description': 'OK'}
            }
        }
    elif version == 'v3_1':
        operation_data = {
            'operation_id': 'example'
        }
    else:
        raise NotImplementedError()  # pragma: no cover

    with pytest.raises(RuntimeError, match='Specification is not loaded'):
        loader.add_operation('/', 'get', operation_data)

    loader.load('empty-paths.yaml')
    assert len(loader.specification.paths) == 0
    operation = loader.add_operation('/', 'get', operation_data)
    assert len(loader.specification.paths) == 1

    path = loader.specification.paths['/']
    assert path.get is operation

    operation = loader.add_operation('/', 'post', operation_data)
    assert path.post is operation


@pytest.mark.parametrize('loader_cls', [LoaderV2, LoaderV3])
def test_default(loader_cls):
    loader = loader_cls.default()
    assert len(loader.specification.paths) == 0
    with pytest.raises(RuntimeError, match='Specification already loaded'):
        loader.load_default()
