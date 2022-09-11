from aiohttp import web

from aiohttp_apiset.parameters.extractor import ParametersExtractor
from aiohttp_apiset.parameters.payload import PayloadReader
from aiohttp_apiset.schema import (
    MediaContentType,
    MediaType,
    Parameter,
    ParameterLocation,
    ParameterStyle,
    Payload,
    Schema,
)
from aiohttp_apiset.validator import ValidationError


async def test_extract_parameters(aiohttp_client):
    parameters = [
        Parameter(
            name='num',
            location=ParameterLocation.query,
            style=ParameterStyle.simple,
            explode=False,
            allow_empty_value=False,
            required=True,
            data=Schema(type_='integer')
        ),
        Parameter(
            name='flag',
            location=ParameterLocation.query,
            style=ParameterStyle.simple,
            explode=False,
            allow_empty_value=False,
            required=False,
            data=Schema(type_='boolean', default=False)
        ),
        Parameter(
            name='obj',
            location=ParameterLocation.query,
            style=ParameterStyle.form,
            explode=False,
            allow_empty_value=False,
            required=False,
            data=Schema(
                type_='object',
                properties={
                    'k1': Schema(type_='integer'),
                    'k2': Schema(type_='boolean')
                },
                required={'k1'}
            )
        )
    ]
    extractor = ParametersExtractor(parameters=parameters)

    async def handler(request):
        try:
            data = await extractor.extract(request)
        except ValidationError as exc:
            return web.json_response(exc.to_flat())
        else:
            return web.json_response({'data': data})

    app = web.Application()
    app.router.add_get('/', handler)
    client = await aiohttp_client(app)

    rep = await client.get('/', params={'num': '1'})
    assert rep.status == 200, (await rep.text())
    data = (await rep.json())['data']
    assert data == {'num': 1, 'flag': False}

    rep = await client.get('/', params={'num': '1', 'flag': 'true'})
    assert rep.status == 200, (await rep.text())
    data = (await rep.json())['data']
    assert data == {'num': 1, 'flag': True}

    rep = await client.get('/', params={'num': 'x'})
    assert rep.status == 200, (await rep.text())
    data = await rep.json()
    assert data == {'num': ["invalid literal for int() with base 10: 'x'"]}

    rep = await client.get('/')
    assert rep.status == 200, (await rep.text())
    data = await rep.json()
    assert data == {'.': ["'num' is a required property"]}

    rep = await client.get('/', params={'num': '1', 'obj': 'k2,v'})
    assert rep.status == 200, (await rep.text())
    data = await rep.json()
    assert data == {'obj': ['Not valid value for bool: v']}


async def test_extract_payload(aiohttp_client):
    payload = Payload(
        media_types=[
            MediaType(
                name=None,
                encodings=[],
                content_type=MediaContentType.json,
                data=Schema(
                    type_='object',
                    properties={
                        'key': Schema(type_='string')
                    },
                    required={'key'}
                )
            )
        ],
        required=True
    )
    payload_reader = PayloadReader()
    extractor = ParametersExtractor(parameters=[], payload=payload, payload_reader=payload_reader)

    async def handler(request):
        try:
            data = await extractor.extract(request)
        except ValidationError as exc:
            return web.json_response(exc.to_flat())
        else:
            return web.json_response({'data': data})

    app = web.Application()
    app.router.add_post('/', handler)
    client = await aiohttp_client(app)

    rep = await client.post('/', json={'key': 'value'})
    assert rep.status == 200, (await rep.text())
    data = (await rep.json())['data']
    assert data == {'payload': {'key': 'value'}}

    rep = await client.post('/', json={})
    assert rep.status == 200, (await rep.text())
    data = await rep.json()
    assert data == {'payload': ["'key' is a required property"]}

    rep = await client.post('/', data=b'', headers={'Content-Type': 'text/plain'})
    assert rep.status == 200, (await rep.text())
    data = await rep.json()
    assert data == {'payload': ['Unsupported content type: text/plain']}
