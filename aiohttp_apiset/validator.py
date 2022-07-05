from types import GeneratorType
from typing import Any

from jsonschema import draft202012_format_checker
from jsonschema.validators import Draft202012Validator

from .errors import Errors


class ConvertTo(BaseException):
    def __init__(self, new_value):
        self.new_value = new_value


class WithMessages(BaseException):
    def __init__(self, *messages):
        self.messages = messages


class Validator:
    check_schema = True
    format_checker = draft202012_format_checker

    @classmethod
    def factory(cls, *args, **kwargs):
        return Draft202012Validator(*args, format_checker=cls.format_checker, **kwargs)

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
        if isinstance(v, GeneratorType):
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

        def wrapper(f):
            @cls.format_checker.checks(name, raises)
            def conv(value):
                v = cls._try_messages(f(value))
                raise ConvertTo(v)

        return wrapper

    @classmethod
    def checks_format(cls, name, raises=()):
        raises = cls._raises(raises)

        def wrapper(f):
            @cls.format_checker.checks(name, raises)
            def conv(value):
                v = cls._try_messages(f(value))
                return v is not False

        return wrapper

    def __init__(self, schema):
        self.schema = schema
        self.validator = self.factory(schema)
        if self.check_schema:
            self.validator.check_schema(schema)

    def validate(self, value: Any) -> Any:
        errors = ValidationError()
        for error in self.validator.descend(value, self.schema):
            if error.path:
                path = tuple(error.path)
            else:
                path = ()
            if isinstance(error.cause, ConvertTo):
                if not path:
                    return error.cause.new_value
                base = value
                *path, tail = path  # type: ignore
                for i in path:
                    base = base[i]
                base[tail] = error.cause.new_value
                continue
            elif isinstance(error.cause, WithMessages):
                messages = error.cause.messages
            else:
                messages = error.message,
            errors[path].update(messages)  # type: ignore
        if errors:
            raise errors
        return value


class ValidationError(Errors, Exception):
    pass
