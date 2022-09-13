from typing import Any, Callable, Mapping, Optional, Union

from ..schema import Schema


EMPTY = object()


def convert_primitive(schema: Optional[Schema], raw_value: str) -> Any:
    if schema is None or schema.type_ is None:
        return raw_value
    if isinstance(schema.type_, list):
        type_names = set(schema.type_)
    else:
        type_names = {schema.type_}
    last_exc = None
    converted_value = EMPTY
    for type_name in type_names:
        converter = CONVERTERS.get(type_name)
        if converter is None:
            continue
        if isinstance(converter, Mapping):
            converter = converter.get(schema.format_, converter[None])
        assert callable(converter)
        try:
            converted_value = converter(raw_value)
        except ValueError as exc:
            last_exc = exc
    if converted_value is not EMPTY:
        return converted_value
    if last_exc is not None:
        raise last_exc
    return raw_value


def _convert_boolean(value: str) -> bool:
    if isinstance(value, str):
        value = value.lower()
    if value in ('true', '1'):
        return True
    elif value in ('false', '0'):
        return False
    else:
        raise ValueError('Not valid value for bool: {}'.format(value))


def _convert_null(value: str):
    if value.lower() == 'null' or not value:
        return None
    raise ValueError('Not valid value for null: {}'.format(value))


Converter = Callable[[Any], Any]
FormatConverters = Mapping[Optional[str], Converter]

CONVERTERS: Mapping[str, Union[FormatConverters, Converter]] = {
    'boolean': _convert_boolean,
    'integer': int,
    'number': {
        None: float,
        'double': float,
        'float': float,
        'int32': int,
        'int64': int,
    },
    'null': _convert_null,
}
