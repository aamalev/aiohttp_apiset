from unittest import mock

import pytest
from aiohttp import web

from aiohttp_apiset.parameters.payload import PayloadReader
from aiohttp_apiset.schema import MediaContentType, MediaType, Payload, Schema
from aiohttp_apiset.validator import ValidationError


async def example_reader(request):
    """"""


async def test_payload_reader(aiohttp_client):
    reader = PayloadReader()

    assert len([k for k, v in reader]) == 6

    reader['*/*'] = example_reader
    assert len(reader) == 6
    assert '*/*' in reader
    assert reader['*/*'] is example_reader
    del reader['*/*']
    assert '*/*' not in reader
    with pytest.raises(KeyError):
        reader['*/*']

    reader.freeze()
    with pytest.raises(RuntimeError, match='Cannot add reader to frozen PayloadReader'):
        reader['*/*'] = example_reader
    with pytest.raises(RuntimeError, match='Cannot remove reader from frozen PayloadReader'):
        del reader['*/*']

    async def handler(request):
        payload = Payload(
            media_types=[
                MediaType(
                    name=None,
                    encodings=[],
                    content_type=MediaContentType.binary,
                    data=None
                ),
                MediaType(
                    name='data',
                    encodings=[],
                    content_type=MediaContentType.json,
                    data=Schema(
                        type_='object',
                        properties={'key': Schema(type_='string')}
                    )
                ),
                MediaType(
                    name=None,
                    encodings=[],
                    content_type=MediaContentType.multipart,
                    data=None
                ),
                MediaType(
                    name=None,
                    encodings=[],
                    content_type=MediaContentType.urlencoded,
                    data=None
                ),
                MediaType(
                    name=None,
                    encodings=[],
                    content_type='image/png',
                    data=None
                )
            ],
            required=True
        )
        try:
            data = await reader.read(request, payload)
        except ValidationError as exc:
            return web.json_response(exc.to_tree(), status=400)
        except ValueError as exc:
            return web.json_response({'msg': str(exc)}, status=400)
        else:
            return web.json_response({'data_type': type(data).__name__})

    app = web.Application()
    app.router.add_post('/', handler)
    client = await aiohttp_client(app)

    rep = await client.post('/')
    assert rep.status == 400, await rep.text()
    msg = (await rep.json())['msg']
    assert msg == 'Payload is required'

    rep = await client.post('/', json={'k': 'v'})
    assert rep.status == 200, await rep.text()
    data_type = (await rep.json())['data_type']
    assert data_type == 'dict'

    rep = await client.post('/', data='{"k": ', headers={'Content-Type': 'application/json'})
    assert rep.status == 400, await rep.text()
    msg = (await rep.json())['msg']
    assert msg == 'Expecting value: line 1 column 7 (char 6)'

    rep = await client.post('/', data={'k': 'v'})
    assert rep.status == 200, await rep.text()
    data_type = (await rep.json())['data_type']
    assert data_type == 'dict'

    rep = await client.post('/', json={'key': 1})
    assert rep.status == 400, await rep.text()
    data = (await rep.json())
    assert data == {'key': ["1 is not of type 'string'"]}

    rep = await client.post('/', data=b'k=', headers={'Content-Type': 'multipart/form-data'})
    assert rep.status == 400, await rep.text()
    msg = (await rep.json())['msg']
    assert msg == 'boundary missed for Content-Type: multipart/form-data'

    rep = await client.post('/', data=b'', headers={'Content-Type': 'image/png'})
    assert rep.status == 400, await rep.text()
    msg = (await rep.json())['msg']
    assert msg == 'Can not receive content: image/png'

    rep = await client.post(
        '/',
        data=b'----1234\nContent-Disposition: form-data; name="text"\n\ntext',
        headers={'Content-Type': 'multipart/form-data; boundary=--1234'}
    )
    assert rep.status == 400, await rep.text()
    msg = (await rep.json())['msg']
    assert msg == 'Bad form'

    rep = await client.post('/', data=b'data')
    assert rep.status == 200, await rep.text()
    data_type = (await rep.json())['data_type']
    assert data_type == 'dict'

    rep = await client.post('/', data=b'')
    assert rep.status == 400, await rep.text()
    msg = (await rep.json())['msg']
    assert msg == 'Payload is required'

    rep = await client.post('/', data=b'', headers={'Content-Type': 'text/plain'})
    assert rep.status == 400, await rep.text()
    msg = (await rep.json())['msg']
    assert msg == 'Unsupported content type: text/plain'

    with mock.patch('aiohttp.web.Request.json') as read_json:
        read_json.side_effect = Exception('test')
        rep = await client.post('/', data=b'{}', headers={'Content-Type': 'application/json'})
        assert rep.status == 400, await rep.text()
        msg = (await rep.json())['msg']
        assert msg == 'Bad JSON'


def test_validate_empty_schema():
    reader = PayloadReader()
    data = {}
    validated_data = reader._validate(None, data)
    assert validated_data is data
