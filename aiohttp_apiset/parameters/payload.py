import logging
from collections.abc import MutableMapping
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Iterator,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from aiohttp import web
from multidict import MultiDictProxy

from ..schema import MediaContentType, MediaType, Payload, Schema
from ..validator import ValidationError, Validator
from .form_decoder import FormDecoder


logger = logging.getLogger(__name__)


Reader = Callable[[web.Request, MediaType], Coroutine[None, None, Mapping[str, Any]]]
FormData = MultiDictProxy[Union[str, bytes, web.FileField]]


class PayloadReader(MutableMapping):
    """
    :param payload_parameter_name: Default name for request body parameter
                                  Since in OpenAPI 3 we can not set name for request body,
                                  we will use this value as parameter name
    """
    def __init__(self, form_decoder: Optional[FormDecoder] = None, payload_parameter_name='payload'):
        if form_decoder is None:
            form_decoder = FormDecoder()
        self._form_decoder = form_decoder
        self._payload_parameter_name = payload_parameter_name
        self._frozen = False
        self._map: Dict[Union[MediaContentType, str], Reader] = {
            MediaContentType.any_: self._binary_reader,
            MediaContentType.binary: self._binary_reader,
            MediaContentType.json: self._json_reader,
            MediaContentType.multipart: self._form_reader,
            MediaContentType.text: self._text_reader,
            MediaContentType.urlencoded: self._form_reader,
        }

    def freeze(self):
        self._frozen = True

    async def read(self, request: web.Request, payload: Payload) -> Mapping[str, Any]:
        media_types = {i.content_type: i for i in payload.media_types}
        media_type = media_types.get(request.content_type)
        if media_type is None:
            media_type = media_types.get(MediaContentType.any_)
        if media_type is None:
            raise ValueError('Unsupported content type: {}'.format(request.content_type))
        receiver = self._map.get(media_type.content_type)
        if receiver is None:
            raise ValueError('Can not receive content: {}'.format(request.content_type))
        data = await receiver(request, media_type)
        if not data and payload.required:
            raise ValueError('Payload is required')
        return data

    def __setitem__(self, key: str, value: Reader):
        if self._frozen:
            raise RuntimeError('Cannot add reader to frozen PayloadReader')
        self._map[key] = value

    def __delitem__(self, key: str):
        if self._frozen:
            raise RuntimeError('Cannot remove reader from frozen PayloadReader')
        del self._map[key]

    def __getitem__(self, key: str) -> Reader:
        return self._map[key]

    def __len__(self) -> int:
        return len(self._map)

    def __iter__(self) -> Iterator[Tuple[str, Reader]]:
        return iter(self._map.items())

    def __contains__(self, key: object) -> bool:
        return key in self._map

    async def _form_reader(self, request: web.Request, media_type: MediaType) -> Mapping[str, Any]:
        result: MutableMapping[str, Any] = {}
        try:
            raw_data = await request.post()
            form_data = self._form_decoder.decode(media_type, raw_data)
            result.update(form_data)
        except (ValidationError, ValueError) as e:
            raise e from None
        except Exception:
            logger.exception('Could not read POST data as form')
            raise ValueError('Bad form')
        return result

    async def _json_reader(self, request: web.Request, media_type: MediaType) -> Mapping[str, Any]:
        result = {}
        name = media_type.name or self._payload_parameter_name
        try:
            data = await request.json()
            result[name] = self._validate(media_type.data, data)
        except (ValidationError, ValueError) as e:
            raise e from None
        except Exception:
            logger.exception('Could not read POST data as JSON')
            raise ValueError('Bad JSON')
        return result

    async def _binary_reader(self, request: web.Request, media_type: MediaType) -> Mapping[str, Any]:
        result = {}
        data = await request.read()
        if len(data):
            name = media_type.name or self._payload_parameter_name
            result[name] = data
        return result

    async def _text_reader(self, request: web.Request, media_type: MediaType) -> Mapping[str, Any]:
        result = {}
        data = await request.text()
        if len(data):
            name = media_type.name or self._payload_parameter_name
            result[name] = data
        return result

    @staticmethod
    def _validate(schema: Optional[Schema], data: Any) -> Any:
        if schema is None:
            return data
        validator = Validator(schema.dict())
        return validator.validate(data)
