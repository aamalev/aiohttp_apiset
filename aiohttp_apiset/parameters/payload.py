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

from ..schema import MediaContentType, MediaType, Payload, Schema
from ..validator import ValidationError, Validator


DEFAULT_PARAMETER_NAME = 'payload'

Reader = Callable[[web.Request, MediaType], Coroutine[None, None, Mapping[str, Any]]]


class PayloadReader(MutableMapping):
    def __init__(self):
        self._frozen = False
        self._map: Dict[Union[MediaContentType, str], Reader] = {
            MediaContentType.binary: self._binary_reader,
            MediaContentType.json: self._json_reader,
            MediaContentType.multipart: self._form_reader,
            MediaContentType.urlencoded: self._form_reader,
        }

    def freeze(self):
        self._frozen = True

    async def read(self, request: web.Request, payload: Payload) -> Mapping[str, Any]:
        media_types = {i.content_type: i for i in payload.media_types}
        media_type = media_types.get(request.content_type)
        if media_type is None:
            raise ValueError('Unsupported content type')
        receiver = self._map.get(media_type.content_type)
        if receiver is None:
            raise ValueError('Unsupported content type')
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
        try:
            data = await request.post()
            return self._validate(media_type.data, data)
        except ValueError as e:
            raise e from None
        except Exception:
            raise ValueError('Bad form')

    async def _json_reader(self, request: web.Request, media_type: MediaType) -> Mapping[str, Any]:
        result = {}
        name = media_type.name or DEFAULT_PARAMETER_NAME
        try:
            data = await request.json()
            result[name] = self._validate(media_type.data, data)
        except (ValueError, ValidationError) as e:
            raise e from None
        except Exception:
            raise ValueError('Bad JSON')
        return result

    async def _binary_reader(self, request: web.Request, media_type: MediaType) -> Mapping[str, Any]:
        result = {}
        data = await request.read()
        if len(data):
            name = media_type.name or DEFAULT_PARAMETER_NAME
            result[name] = data
        return result

    def _validate(self, schema: Optional[Schema], data: Any) -> Any:
        if schema is None:
            return data
        validator = Validator(schema.dict())
        return validator.validate(data)
