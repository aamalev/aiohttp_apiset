from typing import Any, Dict, Optional

from aiohttp import web

from ..schema import Parameters, Payload, Schema
from ..validator import ValidationError, Validator
from .payload import PayloadReader
from .source import contains_parameter, get_source, read_value


class ParametersExtractor:
    def __init__(
        self,
        parameters: Parameters,
        payload: Optional[Payload] = None,
        payload_reader: Optional[PayloadReader] = None
    ):
        self._parameters = parameters
        self._payload = payload
        self._payload_reader = payload_reader

    async def extract(self, request: web.Request) -> Dict[str, Any]:
        errors = ValidationError()
        result = self._extract_parameters(request, errors)
        result.update(await self._extract_payload(request, errors))
        if errors:
            raise errors
        return result

    def _extract_parameters(self, request: web.Request, errors: ValidationError) -> Dict[str, Any]:
        result = {}
        schema_properties = {}
        schema_required = set()
        for parameter in self._parameters:
            if parameter.data is not None:
                schema_properties[parameter.name] = parameter.data
            source = get_source(request, parameter.location)
            if contains_parameter(source, parameter):
                try:
                    value = read_value(source, parameter)
                except ValueError as exc:
                    errors[parameter.name].add(str(exc))
                    continue
            else:
                if parameter.data is not None and parameter.data.default is not None:
                    value = parameter.data.default
                else:
                    if parameter.required:
                        schema_required.add(parameter.name)
                    continue
            result[parameter.name] = value
        try:
            schema = Schema(type_='object', properties=schema_properties, required=schema_required)
            schema_data = schema.dict()
            validator = Validator(schema_data)
            result = validator.validate(result)
        except ValidationError as exc:
            errors.update(exc)
        return result

    async def _extract_payload(self, request: web.Request, errors: ValidationError) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self._payload_reader is None:
            return result
        has_payload = request.method in request.POST_METHODS
        has_payload = has_payload and self._payload is not None
        if not has_payload:
            return result
        try:
            assert self._payload is not None
            result.update(await self._payload_reader.read(request, self._payload))
        except ValidationError as exc:
            errors['payload'].update(exc)
        except ValueError as exc:
            errors['payload'].add(str(exc))
        return result
