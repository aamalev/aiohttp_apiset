import pytest

from aiohttp_apiset.openapi.adapter import convert
from aiohttp_apiset.openapi.loader.v2_0 import Loader


def test_convert(data_root):
    loader = Loader()
    loader.add_directory(data_root / 'openapi/v2_0/split')
    loader.load('api/swagger.json')
    spec = convert(loader)
    assert spec.base_path == '/api'
    paths = {i.url: i for i in spec.paths}
    _assert_v2_0_pets_valid(paths['/pets'])
    _assert_v2_0_pet_valid(paths['/pets/{id}'])
    _assert_v2_0_pet_avatar_valid(paths['/pets/{id}/avatar'])


def _assert_v2_0_pets_valid(pets):
    assert pets.location_name is None

    operations = {i.method: i for i in pets.operations}

    get_pets = operations['GET']
    assert get_pets.handler_name is None
    assert get_pets.operation_id == 'findPets'
    assert get_pets.parameters

    params = {i.name: i for i in get_pets.parameters}
    assert params['tags'].location == 'query'
    assert params['tags'].required is False
    assert params['tags'].explode is False
    assert params['tags'].style == 'form'
    assert params['tags'].data.type_ == 'array'
    assert params['tags'].data.items.type_ == 'string'
    assert params['limit'].location == 'query'
    assert params['limit'].required is False
    assert params['limit'].explode is True
    assert params['limit'].style == 'form'
    assert params['limit'].data.type_ == 'integer'

    post_pets = operations['POST']
    assert post_pets.handler_name is None
    assert post_pets.operation_id == 'addPet'
    assert not post_pets.parameters
    assert post_pets.payload.required is True
    assert len(post_pets.payload.media_types) == 1
    media_type = post_pets.payload.media_types[0]
    assert media_type.content_type == 'application/json'
    assert len(media_type.data.all_of) == 2
    assert any([i.properties for i in media_type.data.all_of])
    assert any([i.type_ == 'object' for i in media_type.data.all_of])


def _assert_v2_0_pet_valid(pet):
    operations = {i.method: i for i in pet.operations}

    get_pet = operations['GET']
    assert get_pet.handler_name is None
    assert get_pet.operation_id == 'findPet'
    assert get_pet.parameters

    update_pet = operations['PUT']
    assert update_pet.handler_name is None
    assert update_pet.operation_id == 'updatePet'
    assert len(update_pet.parameters) == 1
    assert len(update_pet.payload.media_types) == 1
    media_type = update_pet.payload.media_types[0]
    assert media_type.content_type == 'application/x-www-form-urlencoded'
    assert media_type.data.type_ == 'object'
    assert media_type.data.properties['name'].type_ == 'string'
    assert media_type.data.properties['tag'].type_ == 'string'
    assert media_type.data.properties['description'].type_ == 'integer'
    assert media_type.data.properties['description'].format_ == 'int64'
    assert not media_type.data.required
    assert not media_type.encodings

    delete_pet = operations['DELETE']
    assert delete_pet.handler_name is None
    assert delete_pet.operation_id == 'deletePet'
    assert delete_pet.parameters
    params = {i.name: i for i in delete_pet.parameters}
    assert params['id'].required is True
    assert params['id'].location == 'path'
    assert params['id'].data.type_ == 'integer'


def _assert_v2_0_pet_avatar_valid(pet_avatar):
    operations = {i.method: i for i in pet_avatar.operations}

    post_pet_avatar = operations['POST']
    assert post_pet_avatar.parameters
    assert post_pet_avatar.payload.required is True
    assert len(post_pet_avatar.payload.media_types) == 1
    media_type = post_pet_avatar.payload.media_types[0]
    assert media_type.content_type == 'multipart/form-data'
    assert media_type.data.type_ == 'object'
    assert media_type.data.required == ['image']
    assert media_type.encodings[0].property_name == 'image'
    assert media_type.encodings[0].content_type == 'application/octet-stream'


def test_convert_not_loaded():
    with pytest.raises(RuntimeError, match='Specification is not loaded'):
        convert(Loader())


def test_convert_parameters(data_root):
    loader = Loader()
    loader.add_directory(data_root / 'openapi/v2_0')
    loader.load('parameters.yaml')
    spec = convert(loader)
    assert len(spec.paths) == 1
    path = spec.paths[0]
    assert len(path.operations) == 1
    operation = path.operations[0]
    assert len(operation.parameters) == 3
    locations = {parameter.location for parameter in operation.parameters}
    assert locations == {'header', 'path', 'query'}


def test_convert_multi_body_parameters(data_root):
    loader = Loader()
    loader.add_directory(data_root / 'openapi/v2_0')
    loader.load('multi-body-parameters.yaml')
    with pytest.raises(ValueError, match='There can be one payload at most'):
        convert(loader)


def test_convert_path_and_operation_contains_body(data_root):
    loader = Loader()
    loader.add_directory(data_root / 'openapi/v2_0')
    loader.load('path-and-operation-with-body.yaml')
    with pytest.raises(ValueError, match='There can be one payload at most'):
        convert(loader)


def test_convert_chooses_path_body_paramter(data_root):
    loader = Loader()
    loader.add_directory(data_root / 'openapi/v2_0')
    loader.load('path-with-body.yaml')
    spec = convert(loader)
    assert len(spec.paths) == 1
    path = spec.paths[0]
    assert len(path.operations) == 1
    operation = path.operations[0]
    assert operation.payload is not None
    assert len(operation.payload.media_types) == 1
    media_type = operation.payload.media_types[0]
    assert media_type.data is not None
    assert media_type.data.type_ == 'object'


def test_convert_items_sequence_failed(data_root):
    loader = Loader()
    loader.add_directory(data_root / 'openapi/v2_0')
    loader.load('items-sequence.yaml')
    with pytest.raises(TypeError, match='Could not convert a sequence of schemas into a single schema'):
        convert(loader)
