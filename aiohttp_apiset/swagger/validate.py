from functools import partial

from jsonschema import Draft4Validator, draft4_format_checker

ERROR_TYPE = "Not valid value '{}' for type {}:{}"


def to_bool(value):
    if value in ('true', '1'):
        return True
    elif value in ('false', '0'):
        return False
    else:
        raise ValueError('Not valid value for bool: {}'.format(value))


types_mapping = {
    'boolean': to_bool,
    'integer': int,
    'number': {
        None: float,
        'integer': int,
        'float': float,
        'double': float,
    },
}


def convert(name, value, sw_type, sw_format, errors):
    conv = types_mapping.get(sw_type, lambda x: x)

    if isinstance(conv, dict):
        conv = conv.get(sw_format, conv[None])

    if sw_type in ('string', 'file'):
        return value
    elif isinstance(value, (list, tuple)):
        result = []
        for i, v in enumerate(value):
            try:
                result.append(conv(v))
            except (ValueError, TypeError):
                errors['{}.{}'.format(name, i)].add(
                    ERROR_TYPE.format(v, sw_type, sw_format)
                )
        return result
    else:
        try:
            return conv(value)
        except (ValueError, TypeError):
            errors[name].add(
                ERROR_TYPE.format(value, sw_type, sw_format)
            )


class Validator:
    factory = partial(
        Draft4Validator,
        format_checker=draft4_format_checker)

    def __init__(self, schema):
        self.schema = schema
        self.validator = self.factory(schema)

    def validate(self, value, errors):
        for error in self.validator.descend(value, self.schema):
            param = '.'.join(map(str, error.path))
            errors[param].add(error.message)
        return value


COLLECTION_SEP = {'csv': ',', 'ssv': ' ', 'tsv': '\t', 'pipes': '|'}


def get_collection(source, name, collection_format, default):
    """get collection named `name` from the given `source` that
    formatted accordingly to `collection_format`.
    """
    if collection_format in COLLECTION_SEP:
        separator = COLLECTION_SEP[collection_format]
        value = source.get(name, None)
        if value is None:
            return default
        return value.split(separator)
    if collection_format == 'brackets':
        return source.getall(name + '[]', default)
    else:                       # format: multi
        return source.getall(name, default)
