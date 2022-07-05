from typing import Any, Mapping, Union

from aiohttp import web
from multidict import MultiDictProxy

from ..schema import Parameter, ParameterLocation, ParameterStyle
from .converter import convert_primitive


Source = Union[Mapping[str, str], MultiDictProxy[str]]


EMPTY = object()


def get_source(request: web.Request, location: ParameterLocation) -> Source:
    if location == ParameterLocation.query:
        return request.query
    if location == ParameterLocation.header:
        return request.headers
    if location == ParameterLocation.path:
        return request.match_info
    if location == ParameterLocation.cookie:
        return request.cookies
    raise NotImplementedError()  # pragma: no cover


def contains_parameter(source: Source, parameter: Parameter) -> bool:
    return (
        _contains_parameter_deep_object(source, parameter) or
        _contains_parameter_form_object(source, parameter) or
        parameter.name in source
    )


def _contains_parameter_deep_object(source: Source, parameter: Parameter) -> bool:
    if parameter.style == ParameterStyle.deep_object:
        prefix = '{}['.format(parameter.name)
        result = any(key.startswith(prefix) for key in source.keys())
    else:
        result = False
    return result


def _contains_parameter_form_object(source: Source, parameter: Parameter) -> bool:
    if not (parameter.style == ParameterStyle.form and parameter.explode):
        return False
    if not (parameter.data and parameter.data.type_):
        return False
    if isinstance(parameter.data.type_, list):
        types = set(parameter.data.type_)
    else:
        types = {parameter.data.type_}
    if 'object' not in types:
        return False
    if parameter.data.required:
        required_properties = set(parameter.data.required)
        all_properties = set(source.keys())
        missing_properties = required_properties - all_properties
        result = len(missing_properties) == 0
    elif parameter.data.properties:
        properties = list(parameter.data.properties.keys())
        result = any(key in source for key in properties)
    else:
        result = False
    return result


def _read_value_array(source: Source, parameter: Parameter) -> Any:
    if parameter.name not in source:
        return EMPTY
    if (
        isinstance(source, MultiDictProxy) and
        parameter.location != ParameterLocation.header and
        parameter.explode
    ):
        values = source.getall(parameter.name)
        if values == ['']:
            return None
    else:
        raw_values = source[parameter.name]
        if raw_values:
            values = parameter.parse_array_values(raw_values)
        else:
            return None
    assert parameter.data is not None
    schema = parameter.data.items
    values = [convert_primitive(schema, value) for value in values]
    return values


def _read_value_object(source: Source, parameter: Parameter) -> Any:
    assert parameter.data is not None

    if parameter.style == ParameterStyle.form and parameter.explode:
        if parameter.data.properties:
            raw_properties = {
                key: value
                for key, value in source.items()
                if key in parameter.data.properties
            }
        else:
            raw_properties = {}
    elif parameter.style == ParameterStyle.deep_object:
        prefix = '{}['.format(parameter.name)
        prefix_len = len(prefix)
        raw_properties = {}
        for key, value in source.items():
            if key.startswith(prefix):
                raw_properties[key[prefix_len:-1]] = value
    else:
        raw_value = source[parameter.name]
        raw_properties = parameter.parse_object_properties(raw_value)

    if parameter.data.properties is None:
        result = raw_properties
    else:
        result = {}
        for property_name, value_schema in parameter.data.properties.items():
            if property_name in raw_properties:
                property_value = raw_properties[property_name]
                result[property_name] = convert_primitive(value_schema, property_value)
            elif value_schema.default is not None:
                result[property_name] = value_schema.default
    if not result:
        return EMPTY
    return result


def _read_value_primitive(source: Source, parameter: Parameter) -> Any:
    if parameter.name not in source:
        return EMPTY

    value = source[parameter.name]
    if parameter.location == ParameterLocation.path:
        if parameter.style == ParameterStyle.label:
            if value.startswith('.'):
                value = value[1:]
        if parameter.style == ParameterStyle.matrix:
            prefix = ';{}='.format(parameter.name)
            if value.startswith(prefix):
                value = value[len(prefix):]

    value = convert_primitive(parameter.data, value)

    return value


VALUE_READERS = {
    'array': _read_value_array,
    'boolean': _read_value_primitive,
    'integer': _read_value_primitive,
    'number': _read_value_primitive,
    'null': _read_value_primitive,
    'object': _read_value_object,
    'string': _read_value_primitive
}


def read_value(source: Source, parameter: Parameter) -> Any:
    schema = parameter.data

    if schema is None or schema.type_ is None:
        return source[parameter.name]

    if isinstance(schema.type_, list):
        types = set(schema.type_)
    else:
        types = {schema.type_}

    readers = [
        VALUE_READERS[type_name]
        for type_name in types
        if type_name in VALUE_READERS
    ]

    value, last_exc = EMPTY, None
    for reader in readers:
        try:
            value = reader(source, parameter)
        except ValueError as exc:
            last_exc = exc
        else:
            if value is not EMPTY:
                return value

    if last_exc is not None:
        raise last_exc

    raise ValueError('Parameter {} not found'.format(parameter.name))
