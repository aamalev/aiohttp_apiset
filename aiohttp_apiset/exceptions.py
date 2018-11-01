import json
from collections import Mapping, defaultdict

from aiohttp.web_exceptions import HTTPBadRequest


class Errors(Mapping):
    def __init__(self, *args, **kwargs):
        self._errors = args
        self._child_errors = {}
        for k, v in kwargs.items():
            if isinstance(v, str):
                v = Errors(v)
            elif isinstance(v, (list, tuple)):
                v = Errors(*v)
            elif not isinstance(v, Errors):
                raise ValueError(v)
            self._child_errors[k] = v

    def __getitem__(self, item):
        if item is None:
            return self
        elif not isinstance(item, (tuple, list)):
            item = item,
        err = self
        for i in item:
            err = err._child_errors.setdefault(i, Errors())
        return err

    def __getattr__(self, item):
        return self[item]

    def __iter__(self):
        if self._errors:
            yield
        yield from self._child_errors

    def __len__(self):
        return len(self._child_errors) + bool(self._errors)

    def __repr__(self, level=0):
        result = ''
        if not level:
            result = '<{}'.format(type(self).__name__)
        pref = ''
        if self._child_errors:
            pref = '\n' + '  ' * (level + 1)
        if self._errors:
            result += pref + repr(set(self._errors))
        for k, v in self._child_errors.items():
            result += pref + str(k) + ': ' + v.__repr__(level + 1)
        if level:
            return result
        else:
            return result + '>'

    def add(self, *args):
        *path, value = args
        if isinstance(value, (tuple, list)):
            *path, value = value

        if path:
            self[path].add(value)
        elif value not in self._errors:
            self._errors += value,

    def extend(self, seq):
        for i in seq:
            self.add(i)

    def update(self, values):
        if isinstance(values, (list, tuple)):
            for val in values:
                self.add(val)
        elif isinstance(values, Errors):
            self.extend(values._errors)
            for k, v in values._child_errors.items():
                self[k].update(v)
        else:
            raise ValueError(values)

    def to_tree(self, self_key='.'):
        if self._child_errors:
            pass
        elif self._errors:
            return list(self._errors)
        else:
            return
        result = {}
        for k, v in self._child_errors.items():
            value = v.to_tree(self_key=self_key)
            if value:
                result[str(k)] = value
        if self._errors:
            result[self_key] = list(self._errors)
        if result:
            return result

    def to_flat(self, separator='.', path=None):
        result = defaultdict(list)
        if self._errors:
            result[path if path else separator] = list(self._errors)
        for k, v in self._child_errors.items():
            if path is not None:
                k = separator.join((path, str(k)))
            for p, e in v.to_flat(separator=separator, path=str(k)).items():
                result[p].extend(e)
        return result


class ValidationError(Errors, HTTPBadRequest):  # type: ignore
    def __init__(self, *args, **kwargs):
        HTTPBadRequest.__init__(self)
        Errors.__init__(self, *args, **kwargs)
        self._reason = self

    async def prepare(self, request, dumps=json.dumps):
        self.text = dumps({'errors': self.to_tree()})
        self.content_type = 'application/json'
        return await super().prepare(request)

    def update(self, arg=None, **kwargs):  # type: ignore
        if isinstance(arg, (list, tuple, Errors)):
            Errors.update(self, arg)
        elif not arg:
            HTTPBadRequest.update(self, **kwargs)
        else:
            HTTPBadRequest.update(self, arg, **kwargs)

    def __bool__(self):
        return bool(Errors.__len__(self))
