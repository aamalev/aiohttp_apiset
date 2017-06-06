import importlib
from collections.abc import Mapping
from importlib import import_module

import yaml

from ..utils import import_obj


class OperationIdMapping(Mapping):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._operations = []
        self.add(*args, **kwargs)

    def __getitem__(self, key):
        for om in self._operations:
            try:
                if isinstance(om, Mapping):
                    return om[key]
                else:
                    return getattr(om, key)
            except (KeyError, AttributeError):
                pass

        raise KeyError(key)

    def __iter__(self):
        raise NotImplementedError()

    def __len__(self):
        return len(self._operations)

    @classmethod
    def _from_str(cls, name):
        try:
            return import_module(name)
        except ImportError:
            pass

        try:
            return import_obj(name)
        except AttributeError:
            pass

        raise ImportError(name)

    def add(self, *args, **kwargs):
        """ Add new mapping from args and kwargs

        >>> om = OperationIdMapping()
        >>> om.add(
        ...     OperationIdMapping(),
        ...     'aiohttp_apiset.swagger.operations',  # any module
        ...     getPets='mymod.handler',
        ...     getPet='mymod.get_pet',
        ... )
        >>> om['getPets']
        'mymod.handler'

        :param args: str, Mapping, module or obj
        :param kwargs: operationId='handler' or operationId=handler
        """
        for arg in args:
            if isinstance(arg, str):
                self._operations.append(self._from_str(arg))
            else:
                self._operations.append(arg)
        if kwargs:
            self._operations.append(kwargs)


def get_docstring_swagger(handler):
    if isinstance(handler, str):
        h = handler
        p = []
        while isinstance(h, str):
            try:
                h = importlib.import_module(h)
                break
            except ImportError:
                if '.' not in h:
                    raise ImportError(handler)
                h, t = h.rsplit('.', 1)
                p.append(t)
                continue
        for i in reversed(p):
            h = getattr(h, i, None)
            if h is None:
                raise ImportError(handler)
        docstr = h.__doc__
    else:
        docstr = handler.__doc__

    if docstr:
        ds = docstr.rsplit('    ---', maxsplit=1)
        if len(ds) == 1:
            return
        swagger_yaml = ds[-1]
        operation = yaml.load(swagger_yaml)
        if isinstance(operation, dict):
            return operation
