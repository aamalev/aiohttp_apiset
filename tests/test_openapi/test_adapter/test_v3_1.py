import pytest

from aiohttp_apiset.openapi.adapter import convert
from aiohttp_apiset.openapi.loader.v3_1 import Loader


def test_convert(data_root):
    loader = Loader()
    loader.add_directory(data_root / 'openapi/v3_1/split')
    loader.load('api/openapi.json')
    spec = convert(loader)

    assert spec.base_path == '/api'
    paths = {i.url: i for i in spec.paths}

    _assert_v3_1_pets_valid(paths['/pets'])
    _assert_v3_1_pet_valid(paths['/pets/{id}'])
    _assert_v3_1_pet_avatar_valid(paths['/pets/{id}/avatar'])


def _assert_v3_1_pets_valid(pets):
    assert pets.location_name is None

    operations = {i.method: i for i in pets.operations}

    get_pets = operations['GET']
    assert get_pets.handler_name is None
    assert get_pets.operation_id == 'findPets'
    assert get_pets.parameters

    params = {i.name: i for i in get_pets.parameters}
    assert params['tags'].location == 'query'
    assert params['tags'].required is False
    assert params['tags'].explode is True
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
    assert media_type.data.dict() == {
        'allOf': [
            {
                'type': 'object',
                'required': ['name'],
                'properties': {
                    'name': {'type': 'string'},
                    'tag': {'type': 'string'},
                }
            },
            {
                'type': 'object',
                'properties': {
                    'avatar': {
                        'type': 'object',
                        'properties': {
                            'file_id': {
                                'type': 'string',
                                'format': 'uuid'
                            }
                        }
                    }
                }
            }
        ]
    }


def _assert_v3_1_pet_valid(pet):
    operations = {i.method: i for i in pet.operations}

    get_pet = operations['GET']
    assert get_pet.handler_name is None
    assert get_pet.operation_id == 'findPet'
    assert get_pet.parameters

    delete_pet = operations['DELETE']
    assert delete_pet.handler_name is None
    assert delete_pet.operation_id == 'deletePet'
    assert delete_pet.parameters
    params = {i.name: i for i in delete_pet.parameters}
    assert params['id'].required is True
    assert params['id'].location == 'path'
    assert params['id'].data.type_ == 'integer'


def _assert_v3_1_pet_avatar_valid(pet_avatar):
    operations = {i.method: i for i in pet_avatar.operations}

    post_pet_avatar = operations['POST']
    assert post_pet_avatar.parameters
    assert post_pet_avatar.payload.required is True
    assert len(post_pet_avatar.payload.media_types) == 3
    media_types = {i.content_type: i for i in post_pet_avatar.payload.media_types}
    media_type = media_types['multipart/form-data']
    encoding = media_type.encodings[0]
    assert encoding.property_name == 'image'
    assert encoding.content_type == 'image/png'
    header = encoding.headers[0]
    assert header.name == "X-Rate-Limit-Limit"
    assert header.data.type_ == 'integer'

    media_type = media_types['image/png']
    assert media_type.data.type_ == 'string'
    assert media_type.data.content_media_type == 'image/png'
    assert media_type.data.content_encoding == 'base64'

    assert '*/*' in media_types


def test_convert_not_loaded():
    with pytest.raises(RuntimeError, match='Specification is not loaded'):
        convert(Loader())


def test_convert_empty_paths(data_root):
    loader = Loader()
    loader.add_directory(data_root / 'openapi/v3_1')
    loader.load('empty-paths.yaml')
    spec = convert(loader)
    assert len(spec.paths) == 0


def test_convert_parameters(data_root):
    loader = Loader()
    loader.add_directory(data_root / 'openapi/v3_1')
    loader.load('parameters.yaml')
    spec = convert(loader)
    assert len(spec.paths) == 1
    path = spec.paths[0]
    assert len(path.operations) == 1
    operation = path.operations[0]
    locations = {i.location for i in operation.parameters}
    assert set(locations) == {'cookie', 'header', 'path', 'query'}
    parameters = {i.name: i for i in operation.parameters}
    assert parameters['filter'].data is not None
