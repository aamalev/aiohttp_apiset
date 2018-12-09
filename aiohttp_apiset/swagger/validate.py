import types

from jsonschema import draft4_format_checker, ValidationError
from jsonschema.validators import Draft4Validator, extend

ERROR_TYPE = "Not valid value '{}' for type {}:{}"


def to_bool(value):
    if isinstance(value, str):
        value = value.lower()
    if value in ('true', '1', ''):
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


class ConvertTo(BaseException):
    def __init__(self, new_value):
        self.new_value = new_value


class WithMessages(BaseException):
    def __init__(self, *messages):
        self.messages = messages


class RequiredException(ValidationError):
    def __init__(self, *args, prop, **kwargs):
        super().__init__(*args, **kwargs)
        self.prop = prop


class Validator:
    check_schema = True
    format_checker = draft4_format_checker

    @classmethod
    def factory(cls, *args, **kwargs):
        factory = extend(Draft4Validator, dict(required=cls._required))
        return factory(*args, format_checker=cls.format_checker, **kwargs)

    @staticmethod
    def _required(validator, required, instance, schema):
        if not validator.is_type(instance, "object"):
            return
        for property in required:
            if property not in instance:
                yield RequiredException("required", prop=property)

    @staticmethod
    def _raises(raises):
        r = [ConvertTo, WithMessages]
        if isinstance(raises, (list, tuple)):
            r.extend(raises)
        else:
            r.append(raises)
        return tuple(r)

    @staticmethod
    def _try_messages(v):
        if isinstance(v, types.GeneratorType):
            messages = []
            try:
                while True:
                    messages.append(next(v))
            except StopIteration as e:
                v = e.value
            if messages:
                raise WithMessages(*messages)
        return v

    @classmethod
    def converts_format(cls, name, raises=()):
        raises = cls._raises(raises)

        def wraper(f):
            @cls.format_checker.checks(name, raises)
            def conv(value):
                v = cls._try_messages(f(value))
                raise ConvertTo(v)
        return wraper

    @classmethod
    def checks_format(cls, name, raises=()):
        raises = cls._raises(raises)

        def wraper(f):
            @cls.format_checker.checks(name, raises)
            def conv(value):
                v = cls._try_messages(f(value))
                return v is not False
        return wraper

    def __init__(self, schema):
        self.schema = schema
        self.validator = self.factory(schema)
        if self.check_schema:
            self.validator.check_schema(schema)

    def validate(self, value, errors):
        for error in self.validator.descend(value, self.schema):
            if error.path:
                path = tuple(error.path)
            else:
                path = ()
            if isinstance(error.cause, ConvertTo):
                if not path:
                    return error.cause.new_value
                base = value
                *path, tail = path
                for i in path:
                    base = base[i]
                base[tail] = error.cause.new_value
                continue
            elif isinstance(error.cause, WithMessages):
                messages = error.cause.messages
            elif isinstance(error, RequiredException):
                path += error.prop,
                messages = error.message,
            else:
                messages = error.message,
            errors[path].update(messages)
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
