from importlib import import_module
from typing import Mapping

from ..utils import import_obj


class OperationIdMapping(Mapping):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._operations = []
        self.add(*args, **kwargs)

    def __getitem__(self, key):
        for om in reversed(self._operations):
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
        ...     'datetime',  # any module
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
