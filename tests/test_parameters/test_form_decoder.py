import base64
import gzip
import io
import xml.etree.ElementTree as ET

import pytest
from aiohttp.web import FileField
from multidict import CIMultiDict, CIMultiDictProxy, MultiDict, MultiDictProxy

from aiohttp_apiset.parameters.form_decoder import FormDecoder
from aiohttp_apiset.schema import Encoding, MediaType, Schema
from aiohttp_apiset.validator import ValidationError


def _create_file(data: bytes) -> FileField:
    return FileField(
        name='file',
        filename='file',
        file=io.BufferedReader(io.BytesIO(data)),  # type: ignore
        content_type='application/octet-stream',
        headers=CIMultiDictProxy(CIMultiDict([]))
    )


def test_decode_primitive():
    decoder = FormDecoder()
    media_type = MediaType(
        encodings=[],
        content_type='multipart/form-data',
        data=Schema(
            type_='object',
            properties={
                'unknown': Schema(),
                'boolean': Schema(
                    type_='boolean'
                ),
                'integer': Schema(
                    type_='integer'
                ),
                'string': Schema(
                    type_='string'
                )
            },
            required=['string']
        )
    )

    form_data = MultiDictProxy(MultiDict([
        ('unknown', 'unknown'),
        ('boolean', 'true'),
        ('integer', '42'),
        ('string', 'x')
    ]))
    result = decoder.decode(media_type, form_data)

    assert result == {
        'unknown': 'unknown',
        'boolean': True,
        'integer': 42,
        'string': 'x'
    }

    with pytest.raises(ValidationError):
        form_data = MultiDictProxy(MultiDict([
            ('boolean', 'true'),
            ('integer', '42'),
        ]))
        decoder.decode(media_type, form_data)


def test_decode_array():
    decoder = FormDecoder()

    media_type = MediaType(
        encodings=[],
        content_type='multipart/form-data',
        data=Schema(
            type_='object',
            properties={
                'string_array': Schema(
                    type_='array',
                    items=Schema(
                        type_='string'
                    )
                ),
                'object_array': Schema(
                    type_='array',
                    items=Schema(
                        type_='object',
                        properties={
                            'key': Schema(
                                type_='string'
                            )
                        }
                    )
                ),
                'nested_object_array': Schema(
                    type_='array',
                    items=Schema(
                        type_='array',
                        items=Schema(
                            type_='object',
                            properties={
                                'key': Schema(
                                    type_='string'
                                )
                            }
                        )
                    )
                ),
                'nested_string_array': Schema(
                    type_='array',
                    items=Schema(
                        type_='array',
                        items=Schema(
                            type_='string'
                        )
                    )
                ),
                'unknown_array': Schema(
                    type_='array'
                )
            }
        )
    )

    form_data = MultiDictProxy(MultiDict([
        ('string_array', 'x1,x2,x3'),
        ('nested_object_array', '[{"key": "v1"}],[{"key": "v2"}]'),
        ('nested_string_array', '["v1"],["v2"]'),
        ('object_array', '{"key": "v1"},{"key": "v2"}'),
        ('unknown_array', 'u1'),
        ('unknown_array', 'u2'),
    ]))
    result = decoder.decode(media_type, form_data)

    assert result == {
        'string_array': ['x1', 'x2', 'x3'],
        'nested_object_array': [[{'key': 'v1'}], [{'key': 'v2'}]],
        'nested_string_array': [['v1'], ['v2']],
        'object_array': [{'key': 'v1'}, {'key': 'v2'}],
        'unknown_array': ['u1', 'u2']
    }

    with pytest.raises(ValueError, match='Unexpected array value format'):
        form_data = MultiDictProxy(MultiDict([
            ('string_array', _create_file(b'unexpected')),
        ]))
        decoder.decode(media_type, form_data)


def test_decode_object():
    decoder = FormDecoder()
    media_type = MediaType(
        encodings=[],
        content_type='multipart/form-data',
        data=Schema(
            type_='object',
            properties={
                'object': Schema(
                    type_='object',
                    properties={
                        'key': Schema(
                            type_='string'
                        ),
                        'inner': Schema(
                            type_='object'
                        )
                    }
                ),
                'empty_object': Schema(
                    type_='object',
                )
            },
            required=['object']
        )
    )

    form_data = MultiDictProxy(MultiDict([
        ('object', r'{"key": "v", "inner": {"k": "v"}}'),
        ('empty_object', '{"key": "value"}')
    ]))
    result = decoder.decode(media_type, form_data)

    assert result == {
        'object': {'key': 'v', 'inner': {'k': 'v'}},
        'empty_object': {'key': 'value'}
    }

    with pytest.raises(ValidationError):
        form_data = MultiDictProxy(MultiDict([
            ('empty_object', '{"key": "value"}')
        ]))
        decoder.decode(media_type, form_data)


def test_decode_with_content_decoders():
    decoder = FormDecoder()
    decoder.register_content_decoder('gzip', lambda x: gzip.decompress(base64.b64decode(x)))

    form_data = MultiDictProxy(MultiDict([
        ('unknown_string', 'unknown'),
        ('base64_string_buf', base64.b64encode(b'b64-data').decode('ascii')),
        ('gzip_string_buf', base64.b64encode(gzip.compress(b'gzip-data')).decode('ascii')),
        ('string_base64_array', ','.join([
            base64.b64encode(b'b64-1').decode('ascii'),
            base64.b64encode(b'b64-2').decode('ascii')
        ]))
    ]))

    media_type = MediaType(
        encodings=[],
        content_type='multipart/form-data',
        data=Schema(
            type_='object',
            properties={
                'unknown_string': Schema(
                    type_='string',
                    content_encoding='unknown'
                ),
                'base64_string_buf': Schema(
                    type_='string',
                    content_encoding='base64'
                ),
                'gzip_string_buf': Schema(
                    type_='string',
                    content_encoding='gzip'
                ),
                'string_base64_array': Schema(
                    type_='array',
                    items=Schema(
                        type_='string',
                        content_encoding='base64'
                    )
                )
            }
        )
    )

    result = decoder.decode(media_type, form_data)

    base64_string_buf = result.pop('base64_string_buf')
    assert base64_string_buf == b'b64-data'

    gzip_string_buf = result.pop('gzip_string_buf')
    assert gzip_string_buf == b'gzip-data'

    string_base64_array = result.pop('string_base64_array')
    assert len(string_base64_array) == 2
    assert string_base64_array[0] == b'b64-1'
    assert string_base64_array[1] == b'b64-2'

    assert result.pop('unknown_string') == 'unknown'

    assert not result


def test_decode_with_custom_media_decoder():
    decoder = FormDecoder()
    decoder.register_media_decoder('application/xml', lambda x, _: ET.fromstring(x))

    form_data = MultiDictProxy(MultiDict([
        ('xml_object', '<key>v</key>'),
        ('additional_xml_object', '<key>v</key>'),
        ('unknown_object', 'unknown-object')
    ]))

    media_type = MediaType(
        encodings=[
            Encoding(
                property_name='additional_xml_object',
                content_type='application/xml',
                headers=[]
            )
        ],
        content_type='multipart/form-data',
        data=Schema(
            type_='object',
            properties={
                'xml_object': Schema(
                    type_='object',
                    content_media_type='application/xml'
                ),
                'unknown_object': Schema(
                    type_='object',
                    content_media_type='application/x-unknown'
                )
            }
        )
    )

    result = decoder.decode(media_type, form_data)

    xml_object = result.pop('xml_object')
    assert xml_object.tag == 'key'
    assert xml_object.text == 'v'

    additional_xml_object = result.pop('additional_xml_object')
    assert additional_xml_object.tag == 'key'
    assert additional_xml_object.text == 'v'

    assert result.pop('unknown_object') == 'unknown-object'

    assert not result


def test_decode_binaries():
    decoder = FormDecoder()

    form_data = MultiDictProxy(MultiDict([
        ('string_buf', _create_file(b'string-buf')),
        ('string_buf_array', _create_file(b'string-buf-item-1')),
        ('string_buf_array', _create_file(b'string-buf-item-2')),
        ('png_image', _create_file(b'png-image')),
        ('jpeg_image', _create_file(b'jpeg-image')),
        ('bmp_images', _create_file(b'bmp-image-1')),
        ('bmp_images', _create_file(b'bmp-image-2')),
        ('webp_images', _create_file(b'webp-image')),
    ]))

    media_type = MediaType(
        encodings=[
            Encoding(
                property_name='png_image',
                content_type='image/png',
                headers=[]
            ),
            Encoding(
                property_name='jpeg_image',
                content_type='image/jpeg',
                headers=[]
            ),
            Encoding(
                property_name='gif_image',
                content_type='image/gif',
                headers=[]
            ),
            Encoding(
                property_name='bmp_images',
                content_type='image/bmp',
                headers=[]
            ),
            Encoding(
                property_name='webp_images',
                content_type='image/webp',
                headers=[]
            )
        ],
        content_type='multipart/form-data',
        data=Schema(
            type_='object',
            properties={
                'string_buf': Schema(
                    type_='string',
                    format_='binary',
                ),
                'string_buf_array': Schema(
                    type_='array',
                    items=Schema(
                        type_='string',
                        format_='binary'
                    )
                ),
                'png_image': Schema(),
                'jpeg_image': Schema(
                    type_='string',
                    format='binary'
                )
            }
        )
    )

    result = decoder.decode(media_type, form_data)

    string_buf = result.pop('string_buf')
    assert string_buf.file.read() == b'string-buf'

    string_buf_array = result.pop('string_buf_array')
    assert len(string_buf_array) == 2
    assert string_buf_array[0].file.read() == b'string-buf-item-1'
    assert string_buf_array[1].file.read() == b'string-buf-item-2'

    png_image = result.pop('png_image')
    assert png_image.file.read() == b'png-image'

    jpeg_image = result.pop('jpeg_image')
    assert jpeg_image.file.read() == b'jpeg-image'

    bmp_images = result.pop('bmp_images')
    assert len(bmp_images) == 2
    assert bmp_images[0].file.read() == b'bmp-image-1'
    assert bmp_images[1].file.read() == b'bmp-image-2'

    webp_images = result.pop('webp_images')
    assert webp_images.file.read() == b'webp-image'

    assert not result


def test_decode_encodings_only():
    decoder = FormDecoder()
    data = MultiDictProxy(MultiDict([
        ('png_image', _create_file(b'png-image')),
    ]))
    media_type = MediaType(
        name=None,
        encodings=[
            Encoding(
                property_name='png_image',
                content_type='image/png',
                headers=[]
            ),
            Encoding(
                property_name='jpeg_image',
                content_type='image/jpeg',
                headers=[]
            ),
        ],
        content_type='multipart/form-data',
        data=Schema(type_='object', properties={})
    )
    result = decoder.decode(media_type, data)
    assert len(result) == 1
    assert result['png_image'].file.read() == b'png-image'


def test_decode_empty_schema():
    decoder = FormDecoder()
    data = MultiDictProxy(MultiDict())
    for schema in [None, Schema(type_='object')]:
        media_type = MediaType(
            name=None,
            encodings=[],
            content_type='multipart/form-data',
            data=schema
        )
        result = decoder.decode(media_type, data)
        assert isinstance(result, MultiDict)
        assert len(result) == 0


def test_decode_non_object_schema():
    decoder = FormDecoder()
    media_type = MediaType(
        name=None,
        encodings=[],
        content_type='multipart/form-data',
        data=Schema(type_='array')
    )
    data = MultiDictProxy(MultiDict())
    with pytest.raises(ValueError, match='Media type schema is not an object'):
        decoder.decode(media_type, data)


def test_decode_json_object_failed():
    decoder = FormDecoder()
    media_type = MediaType(
        name=None,
        encodings=[],
        content_type='multipart/form-data',
        data=Schema(
            type_='object',
            properties={
                'object': Schema(type_='object')
            }
        )
    )

    data = MultiDictProxy(MultiDict([('object', '{')]))
    msg = 'object: Expecting property name enclosed in double quotes'
    with pytest.raises(ValueError, match=msg):
        decoder.decode(media_type, data)

    data = MultiDictProxy(MultiDict([('object', b'[]')]))
    msg = 'Could not decode JSON form property expects mapping, got bytes'
    with pytest.raises(ValueError, match=msg):
        decoder.decode(media_type, data)


def test_decode_content_encoding_failed():
    decoder = FormDecoder()

    def content_decoder(value):
        raise ValueError('Test content encoding decoder failed')

    decoder.register_content_decoder('base64', content_decoder)
    media_type = MediaType(
        name=None,
        encodings=[],
        content_type='multipart/form-data',
        data=Schema(
            type_='object',
            properties={
                'string': Schema(
                    type_='string',
                    content_encoding='base64'
                )
            }
        )
    )

    data = MultiDictProxy(MultiDict([('string', 'x')]))
    msg = 'Test content encoding decoder failed'
    with pytest.raises(ValueError, match=msg):
        decoder.decode(media_type, data)
