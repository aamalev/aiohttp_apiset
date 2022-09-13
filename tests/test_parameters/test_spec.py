import base64
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict

from aiohttp import FormData, web
from multidict import MultiDict

from aiohttp_apiset import Config
from aiohttp_apiset import setup as setup_api
from aiohttp_apiset.config.operation import OperationIdMapping
from aiohttp_apiset.middlewares import jsonify
from aiohttp_apiset.openapi.loader.v2_0 import Loader as LoaderV2
from aiohttp_apiset.openapi.loader.v3_1 import Loader as LoaderV3
from aiohttp_apiset.parameters.payload import PayloadReader


@dataclass
class Payload:
    path: str
    expected_status: int
    expected_data: Dict[str, Any]
    request_kwargs: Dict[str, Any]

    def __str__(self):  # pragma: no cover
        return 'Payload(path={!r}, expected_status={!r})'.format(
            self.path,
            self.expected_status
        )

    async def send(self, client):
        rep = await client.post(self.path, **self.request_kwargs)
        assert rep.status == self.expected_status, str(self) + ' ' + (await rep.text())
        data = await rep.json()
        try:
            assert data == self.expected_data
        except AssertionError:  # pragma: no cover
            print(repr(self))  # noqa
            raise


def to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode('utf-8')


def force_multipart(data: MultiDict[str]) -> FormData:
    form = FormData()
    for k, v in data.items():
        form.add_field(k, v, content_type='text/plain')
    return form


PAYLOAD_COMMON = [
    Payload(
        path='/any',
        expected_status=200,
        expected_data={'type': 'any', 'data': to_base64(b'test-any')},
        request_kwargs={'data': b'test-any'}
    ),
    Payload(
        path='/any-binary',
        expected_status=200,
        expected_data={'type': 'any-binary', 'data': to_base64(b'test-any-binary')},
        request_kwargs={
            'data': b'test-any-binary',
            'headers': {'Content-Type': 'application/octet-stream'}
        }
    ),
    Payload(
        path='/any-binary',
        expected_status=400,
        expected_data={'errors': {'payload': ['Unsupported content type: application/x-www-form-urlencoded']}},
        request_kwargs={'data': {'key': 'test-not-accepts-form'}}
    ),
    Payload(
        path='/json',
        expected_status=400,
        expected_data={'errors': {'payload': ["'key' is a required property"]}},
        request_kwargs={'json': {'k': 'v'}}
    ),
    Payload(
        path='/json',
        expected_status=400,
        expected_data={'errors': {'payload': ['Unsupported content type: application/x-www-form-urlencoded']}},
        request_kwargs={'data': {'key': 'not acceptable'}}
    ),
    Payload(
        path='/json',
        expected_status=200,
        expected_data={'type': 'json', 'data': {'key': 'value'}},
        request_kwargs={'json': {'key': 'value'}}
    ),
    Payload(
        path='/images',
        expected_status=200,
        expected_data={'type': 'image', 'data': to_base64(b'test-png'), 'content_type': 'image/png'},
        request_kwargs={'data': b'test-png', 'headers': {'Content-Type': 'image/png'}}
    ),
    Payload(
        path='/images',
        expected_status=200,
        expected_data={'type': 'image', 'data': to_base64(b'test-jpeg'), 'content_type': 'image/jpeg'},
        request_kwargs={'data': b'test-jpeg', 'headers': {'Content-Type': 'image/jpeg'}}
    ),
    Payload(
        path='/images',
        expected_status=200,
        expected_data={'type': 'image', 'data': to_base64(b'test-gif'), 'content_type': 'image/gif'},
        request_kwargs={'data': b'test-gif', 'headers': {'Content-Type': 'image/gif'}}
    ),
    Payload(
        path='/images',
        expected_status=400,
        expected_data={'errors': {'payload': ['Unsupported content type: image/bmp']}},
        request_kwargs={'data': b'test-bmp', 'headers': {'Content-Type': 'image/bmp'}}
    ),
    Payload(
        path='/string-array',
        expected_status=200,
        # Since there is no information about text/plain schema format in OpenAPI spec, we simply read it as is
        expected_data={'type': 'string-array', 'data': 'test\narray'},
        request_kwargs={'data': b'test\narray', 'headers': {'Content-Type': 'text/plain'}}
    ),
]

PAYLOAD_2_0 = [
    Payload(
        path='/multipart',
        expected_status=200,
        expected_data={
            'type': 'multipart',
            'data': {
                'object_id': '7aa068cd-df1e-43ec-819c-e18c46427d54',
                'city_id': 1,
                'address': 'Address',
                'profile_image': to_base64(b'profile-image-data'),
                'cover_image': to_base64(b'cover-image-data'),
                'photos': [
                    to_base64(b'photo-1'),
                    to_base64(b'photo-2'),
                ],
                'children': ['child1', 'child2']
            }
        },
        request_kwargs={
            'data': MultiDict([
                ('object_id', '7aa068cd-df1e-43ec-819c-e18c46427d54'),
                ('city_id', '1'),
                ('address', 'Address'),
                ('profile_image', BytesIO(b'profile-image-data')),
                ('cover_image', BytesIO(b'cover-image-data')),
                ('photos', BytesIO(b'photo-1')),
                ('photos', BytesIO(b'photo-2')),
                ('children', 'child1,child2'),
            ])
        }
    ),
    Payload(
        path='/multipart',
        expected_status=400,
        expected_data={'errors': {'payload': ['\'city_id\' is a required property']}},
        request_kwargs={
            'data': force_multipart(MultiDict([
                ('address', 'Address')
            ])),
        }
    ),
    Payload(
        path='/multipart',
        expected_status=400,
        expected_data={'errors': {'payload': {'object_id': ["'invalid' is not a 'uuid'"]}}},
        request_kwargs={
            'data': force_multipart(MultiDict([
                ('object_id', 'invalid'),
                ('city_id', '2')
            ])),
        }
    ),
    Payload(
        path='/urlencoded',
        expected_status=200,
        expected_data={
            'type': 'urlencoded',
            'data': {
                'object_id': '7aa068cd-df1e-43ec-819c-e18c46427d54',
                'address': ['City 1', 'City 2']
            }
        },
        request_kwargs={
            'data': {'object_id': '7aa068cd-df1e-43ec-819c-e18c46427d54', 'address': 'City 1,City 2'},
            'headers': {'Content-Type': 'application/x-www-form-urlencoded'}
        }
    )
]

PAYLOAD_3_1 = [
    Payload(
        path='/binary-string',
        expected_status=200,
        expected_data={'type': 'binary-string', 'data': to_base64(b'test-binary-string')},
        request_kwargs={
            'data': b'test-binary-string',
            'headers': {'Content-Type': 'application/octet-stream'}
        }
    ),
    Payload(
        path='/binary-string',
        expected_status=400,
        expected_data={'errors': {'payload': ['Unsupported content type: application/x-www-form-urlencoded']}},
        request_kwargs={'data': {'key': 'test-not-accepts-form'}}
    ),
    Payload(
        path='/multipart',
        expected_status=200,
        expected_data={
            'type': 'multipart',
            'data': {
                'object_id': '7aa068cd-df1e-43ec-819c-e18c46427d54',
                'country_id': 1,
                'city_id': [1, 2],
                'address': {"city": "City"},
                'profile_image': to_base64(b'profile-image-data'),
                'cover_image': to_base64(b'cover-image-data'),
                'photo': to_base64(b'photo-data'),
                'additional_photos': [to_base64(b'photo-1'), to_base64(b'photo-2')],
                'children': ['child1', 'child2'],
                'addresses': [
                    {"city": "City 1"},
                    {"city": "City 2"}
                ],
                # decoder for XML content media type is not registered, so history_metadata is not parsed
                'history_metadata': '<key>value</key>'
            }
        },
        request_kwargs={
            'data': MultiDict([
                ('object_id', '7aa068cd-df1e-43ec-819c-e18c46427d54'),
                ('country_id', '1'),
                ('city_id', '1,2'),
                ('address', '{"city": "City"}'),
                ('profile_image', BytesIO(b'profile-image-data')),
                ('cover_image', to_base64(b'cover-image-data')),
                ('photo', BytesIO(b'photo-data')),
                ('additional_photos', BytesIO(b'photo-1')),
                ('additional_photos', BytesIO(b'photo-2')),
                ('children', 'child1,child2'),
                ('addresses', '{"city": "City 1"},{"city": "City 2"}'),
                ('history_metadata', '<key>value</key>')
            ])
        }
    ),
    Payload(
        path='/multipart',
        expected_status=400,
        expected_data={'errors': {'payload': ['\'country_id\' is a required property']}},
        request_kwargs={
            'data': force_multipart(MultiDict([
                ('object_id', '7aa068cd-df1e-43ec-819c-e18c46427d54'),
            ])),
        }
    ),
    Payload(
        path='/multipart',
        expected_status=400,
        expected_data={'errors': {'payload': ['address: Expecting value: line 1 column 1 (char 0)']}},
        request_kwargs={
            'data': force_multipart(MultiDict([
                ('country_id', '2'),
                ('address', ''),
            ])),
        }
    ),
    Payload(
        path='/multipart',
        expected_status=400,
        expected_data={'errors': {'payload': {'object_id': ["'invalid' is not a 'uuid'"]}}},
        request_kwargs={
            'data': force_multipart(MultiDict([
                ('object_id', 'invalid'),
                ('country_id', '2'),
            ])),
        }
    ),
    Payload(
        path='/multipart',
        expected_status=400,
        expected_data={'errors': {'payload': ['Could not decode base64: Incorrect padding']}},
        request_kwargs={
            'data': force_multipart(MultiDict([
                ('cover_image', 'invalid'),
            ])),
        }
    ),
    Payload(
        path='/urlencoded',
        expected_status=200,
        expected_data={
            'type': 'urlencoded',
            'data': {
                'object_id': '7aa068cd-df1e-43ec-819c-e18c46427d54',
                'address': {'city': 'City'}
            }
        },
        request_kwargs={
            'data': {'object_id': '7aa068cd-df1e-43ec-819c-e18c46427d54', 'address': '{"city": "City"}'},
            'headers': {'Content-Type': 'application/x-www-form-urlencoded'}
        }
    )
]


async def handle_any(request, payload):
    return {
        'type': 'any',
        'data': to_base64(payload)
    }


async def handle_any_binary(request, payload):
    return {
        'type': 'any-binary',
        'data': to_base64(payload)
    }


async def handle_binary_string(request, payload):
    return {
        'type': 'binary-string',
        'data': to_base64(payload)
    }


async def handle_json(request, payload):
    return {
        'type': 'json',
        'data': payload
    }


async def handle_images(request, payload):
    return {
        'type': 'image',
        'data': to_base64(payload),
        'content_type': request.content_type
    }


async def handle_string_array(request, payload):
    return {
        'type': 'string-array',
        'data': payload
    }


async def handle_multipart_v2_0(
    request,
    object_id,
    city_id,
    address,
    profile_image,
    cover_image,
    photos,
    children
):
    return {
        'type': 'multipart',
        'data': {
            'object_id': object_id,
            'city_id': city_id,
            'address': address,
            'profile_image': to_base64(profile_image.file.read()),
            'cover_image': to_base64(cover_image.file.read()),
            'photos': list(map(lambda x: to_base64(x.file.read()), photos)),
            'children': children
        }
    }


async def handle_multipart_v3_1(
    request,
    object_id,
    country_id,
    city_id,
    address,
    profile_image,
    cover_image,
    photo,
    additional_photos,
    children,
    addresses,
    history_metadata
):
    return {
        'type': 'multipart',
        'data': {
            'object_id': object_id,
            'country_id': country_id,
            'city_id': city_id,
            'address': address,
            'profile_image': to_base64(profile_image.file.read()),
            'cover_image': to_base64(cover_image),
            'photo': to_base64(photo.file.read()),
            'additional_photos': list(map(lambda x: to_base64(x.file.read()), additional_photos)),
            'children': children,
            'addresses': addresses,
            'history_metadata': history_metadata
        }
    }


async def handle_urlencoded(request, object_id, address):
    return {
        'type': 'urlencoded',
        'data': {
            'object_id': object_id,
            'address': address
        }
    }


def _create_operation_id_mapping(**kwargs):
    return OperationIdMapping(
        any=handle_any,
        any_binary=handle_any_binary,
        binary_string=handle_binary_string,
        json=handle_json,
        images=handle_images,
        string_array=handle_string_array,
        urlencoded=handle_urlencoded,
        **kwargs
    )


def _create_payload_reader():
    payload_reader = PayloadReader()
    payload_reader['image/jpeg'] = payload_reader._binary_reader
    payload_reader['image/png'] = payload_reader._binary_reader
    payload_reader['image/gif'] = payload_reader._binary_reader
    return payload_reader


def _setup_api(loader, app, operations):
    payload_reader = _create_payload_reader()
    operation_id_mapping = _create_operation_id_mapping(**operations)
    config = Config(
        loader,
        payload_reader=payload_reader,
        operation_id_mapping=operation_id_mapping,
    )
    setup_api(config, app)


async def test_payload_v2_0(aiohttp_client, data_root):
    loader = LoaderV2()
    loader.add_directory(data_root / 'parameters')
    loader.load('payload_v2_0.yaml')
    app = web.Application(middlewares=[jsonify()])
    _setup_api(loader, app, operations={'multipart': handle_multipart_v2_0})

    client = await aiohttp_client(app)
    for payload in PAYLOAD_COMMON + PAYLOAD_2_0:
        await payload.send(client)


async def test_payload_v3_1(aiohttp_client, data_root):
    loader = LoaderV3()
    loader.add_directory(data_root / 'parameters')
    loader.load('payload_v3_1.yaml')
    app = web.Application(middlewares=[jsonify()])
    _setup_api(loader, app, operations={'multipart': handle_multipart_v3_1})

    client = await aiohttp_client(app)
    for payload in PAYLOAD_COMMON + PAYLOAD_3_1:
        await payload.send(client)
