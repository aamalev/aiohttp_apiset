from jsonschema import validate

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
                errors.add(
                    '{}.{}'.format(name, i),
                    ERROR_TYPE.format(v, sw_type, sw_format)
                )
        return result
    else:
        try:
            return conv(value)
        except (ValueError, TypeError):
            errors.add(
                name,
                ERROR_TYPE.format(value, sw_type, sw_format)
            )
