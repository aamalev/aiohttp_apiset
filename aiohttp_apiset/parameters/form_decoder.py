import base64
import json
import logging
from functools import partial
from typing import (
    Any,
    Callable,
    Dict,
    List,
    MutableMapping,
    Optional,
    Set,
    Union,
)

from aiohttp.web import FileField
from multidict import MultiDict, MultiDictProxy

from ..schema import MediaType, Schema
from ..validator import Validator
from .converter import convert_primitive


logger = logging.getLogger(__name__)


ContentDecoder = Callable[[str], Any]
MediaDecoder = Callable[[str, Optional[Schema]], Any]
FormValue = Union[str, bytes, FileField]
FormData = MutableMapping[str, Any]


class FormDecoder:
    def __init__(self):
        self._media_decoders: Dict[str, MediaDecoder] = {}
        self._content_decoders: Dict[str, ContentDecoder] = {'base64': base64.b64decode}

    def register_media_decoder(self, content_type: str, decoder: MediaDecoder):
        """
        Registers a decoder for given content media type
        Decoder takes a raw data as string and optional jsonschema object and returns decoded data
        """
        logger.info('Registered a media decoder for %s', content_type)
        self._media_decoders[content_type] = decoder

    def register_content_decoder(self, content_encoding: str, decoder: ContentDecoder):
        """
        Registers a decoder for given content encoding
        Decoder takes a single string value and returns a decoded value
        """
        logger.info('Registered a content decoder for %s', content_encoding)
        self._content_decoders[content_encoding] = decoder

    def decode(self, media_type: MediaType, raw_form_data: MultiDictProxy[FormValue]) -> FormData:
        form_data = raw_form_data.copy()
        schema = media_type.data

        if schema is None:
            return form_data
        if schema.type_ != 'object':
            raise ValueError('Media type schema is not an object')
        if schema.properties is None:
            return form_data

        untyped_data = self._decode_media_type_encodings(media_type, form_data)
        result = self._decode_object_properties(schema, form_data, untyped_data=untyped_data)

        return result

    def _decode_media_type_encodings(self, media_type: MediaType, raw_data: MultiDict[FormValue]) -> FormData:
        result: FormData = {}

        for encoding in media_type.encodings:
            property_name = encoding.property_name
            if property_name not in raw_data:
                continue
            encoded_value = raw_data.popall(property_name)
            if len(encoded_value) == 1:
                result[property_name] = encoded_value[0]
            else:
                result[property_name] = encoded_value

            if encoding.content_type:
                decoder = self._media_decoders.get(encoding.content_type)
                if decoder:
                    logger.info('Found media decoder for %s', encoding.content_type)
                    result[property_name] = decoder(result[property_name], None)
        return result

    def _decode_object_properties(
        self,
        schema: Schema,
        raw_data: Union[MultiDict[FormValue], FormData],
        validate: bool = True,
        untyped_data: Optional[FormData] = None
    ) -> Union[MultiDict[FormValue], FormData]:
        if schema.properties is None:
            return raw_data

        result: FormData = {}
        if untyped_data is None:
            untyped_data = {}

        for property_name, property_schema in schema.properties.items():
            if property_name not in raw_data:
                continue
            if not property_schema.type_:
                # Most likely contains a binary data, unable to validate
                untyped_data[property_name] = raw_data[property_name]
            elif property_schema.type_ == 'array':
                raw_array = RawArray.create(property_name, property_schema, raw_data)
                untyped_data[property_name] = self._decode_array(property_schema, raw_array, property_name)
            elif property_schema.type_ == 'object':
                untyped_data[property_name] = self._decode_object(
                    property_schema,
                    raw_data[property_name],
                    property_name
                )
            else:
                property_value = raw_data[property_name]
                if isinstance(property_value, FileField):
                    untyped_data[property_name] = property_value
                else:
                    assert isinstance(property_value, str), type(property_value).__name__
                    if property_schema.content_encoding:
                        untyped_data[property_name] = self._decode_primitive(property_schema, property_value)
                    else:
                        result[property_name] = convert_primitive(property_schema, property_value)

        if validate:
            exclude_required = set(untyped_data.keys())
            # prevents provided untyped_data items marked as required
            # if some required item in untyped_data is not provided, _validate call will raise an exception
            # so we do not need extra validation for required properties
            result = self._validate(schema, result, exclude_required=exclude_required)

        result.update(untyped_data)

        return result

    def _decode_object(self, schema: Schema, raw_data: Any, property_name: str) -> FormData:
        content_type = schema.content_media_type
        if not content_type:
            # JSON is the default content type for objects in form data
            content_type = 'application/json'

        decoder = self._media_decoders.get(content_type)

        try:
            if decoder is not None:
                return decoder(raw_data, schema)
            if content_type.lower() == 'application/json':
                return self._decode_object_json(schema, raw_data)
        except ValueError as exc:
            raise ValueError('{}: {}'.format(property_name, exc))

        logger.info('Media decoder not found for %s', content_type)
        return raw_data

    def _decode_object_json(self, schema: Schema, raw_data: Union[FormData, str]) -> Any:
        if isinstance(raw_data, str):
            json_data = json.loads(raw_data)
        else:
            json_data = raw_data
        if not isinstance(json_data, dict):
            type_name = type(raw_data).__name__
            raise ValueError('Could not decode JSON form property expects mapping, got {}'.format(type_name))

        return self._decode_object_properties(schema, json_data)

    def _decode_array(
        self,
        schema: Schema,
        raw_data: Union['RawArray', List[Any]],
        property_name: str
    ) -> List[Any]:
        if isinstance(raw_data, RawArray):
            if raw_data.is_parsed:
                return raw_data.items
            raw_items = raw_data.items
        else:
            raw_items = raw_data

        assert schema.items is not None

        convert: Callable[[Any], Any]
        if schema.items.type_ == 'object':
            convert = partial(self._decode_object_properties, schema.items, validate=False)
        elif schema.items.type_ == 'array':
            convert = partial(self._decode_array, schema.items, property_name=property_name)
        else:
            if schema.items.content_encoding:
                convert = partial(self._decode_primitive, schema.items)
            else:
                convert = partial(convert_primitive, schema.items)

        items = list(map(convert, raw_items))

        return items

    def _decode_primitive(self, schema: Schema, raw_data: Any) -> Any:
        assert schema.content_encoding is not None
        decoder = self._content_decoders.get(schema.content_encoding)
        if decoder:
            try:
                return decoder(raw_data)
            except ValueError as exc:
                raise ValueError('Could not decode {}: {}'.format(schema.content_encoding, exc))
        logger.info('Content decoder for %r is not found', schema.content_encoding)
        return raw_data

    @staticmethod
    def _validate(schema: Schema, data: Any, exclude_required: Optional[Set[str]] = None) -> Any:
        schema_data = schema.dict()
        required = schema_data.get('required')
        if required and exclude_required:
            schema_data['required'] = list(set(required) - exclude_required)
        validator = Validator(schema_data)
        return validator.validate(data)


class RawArray:
    def __init__(self, items: List[Any], *, is_parsed: bool = False):
        self.items = items
        self.is_parsed = is_parsed

    @classmethod
    def create(
        cls,
        property_name: str,
        property_schema: Schema,
        form_data: Union[MultiDict[FormValue], FormData]
    ) -> 'RawArray':
        # Arrays also may contain a binary data
        # Binary data uses multiple values for same key
        # Other types contains a single comma-separated value

        if property_schema.items:
            is_unknown_item = property_schema.items.type_ is None
            is_file_item = property_schema.items.type_ == 'file'
            is_binary_item = property_schema.items.type_ == 'string' and property_schema.items.format_ == 'binary'
            is_multi_item = any([is_unknown_item, is_file_item, is_binary_item])
        else:
            is_multi_item = True
        if isinstance(form_data, MultiDict) and is_multi_item:
            return cls(form_data.getall(property_name), is_parsed=True)

        property_value = form_data[property_name]
        if isinstance(property_value, (FileField, bytes)):
            # We already parsed files in the section above
            # If we got any other value than string, this is an error
            raise ValueError('Unexpected array value format')

        assert isinstance(property_value, str)

        is_complex = (
            property_schema.items and
            property_schema.items.type_ in ['object', 'array']
        )
        if is_complex:
            return cls(json.loads('[{}]'.format(property_value)))

        return cls(property_value.split(','))
