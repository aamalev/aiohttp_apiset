from collections import defaultdict
from collections.abc import Mapping
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


RawChildError = Union[str, Tuple[str], List[str], 'Errors']
Item = Optional[Union[str, Tuple[str], List[str]]]
TreeRepr = Union[Dict[str, Any], List[str]]
FlatRepr = Dict[str, List[str]]


class Errors(Mapping):
    def __init__(self, *args: str, **kwargs: RawChildError):
        self._errors: Tuple[str, ...] = args
        self._child_errors: Dict[str, 'Errors'] = {}
        for k, v in kwargs.items():
            if isinstance(v, str):
                v = Errors(v)
            elif isinstance(v, (list, tuple)):
                v = Errors(*v)
            elif not isinstance(v, Errors):
                raise TypeError('Unexpected error type: {!r}'.format(v))
            self._child_errors[k] = v

    def __getitem__(self, item: Item) -> 'Errors':
        if item is None:
            return self
        elif not isinstance(item, (tuple, list)):
            item = item,
        err = self
        for i in item:
            err = err._child_errors.setdefault(i, Errors())
        return err

    def __getattr__(self, item: Item) -> 'Errors':
        return self[item]

    def __iter__(self):
        if self._errors:
            yield
        yield from self._child_errors

    def __len__(self) -> int:
        return len(self._child_errors) + bool(self._errors)

    def __bool__(self) -> bool:
        return bool(len(self))

    def __repr__(self, level: int = 0) -> str:
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

    def add(self, *args: Item):
        *path, value = args
        if isinstance(value, (tuple, list)):
            *path, value = value  # type: ignore

        if path:
            self[path].add(value)  # type: ignore
        elif value not in self._errors:
            self._errors += (value,)  # type: ignore

    def extend(self, seq: Sequence[Item]):
        for i in seq:
            self.add(i)

    def update(self, values: Union[List, Tuple, 'Errors']):
        if isinstance(values, (list, tuple)):
            for val in values:
                self.add(val)
        elif isinstance(values, Errors):
            self.extend(values._errors)
            for k, v in values._child_errors.items():
                self[k].update(v)
        else:
            raise TypeError('Unexpected values: {!r}'.format(values))

    def to_tree(self, self_key: str = '.') -> Optional[TreeRepr]:
        if self._child_errors:
            pass
        elif self._errors:
            return list(self._errors)
        else:
            return None
        result = {}
        for k, v in self._child_errors.items():
            value = v.to_tree(self_key=self_key)
            if value:
                result[str(k)] = value
        if self._errors:
            result[self_key] = list(self._errors)
        if result:
            return result
        return None

    def to_flat(self, separator: str = '.', path: Optional[str] = None) -> FlatRepr:
        result = defaultdict(list)
        if self._errors:
            result[path if path else separator] = list(self._errors)
        for k, v in self._child_errors.items():
            if path is not None:
                k = separator.join((path, str(k)))
            for p, e in v.to_flat(separator=separator, path=str(k)).items():
                result[p].extend(e)
        return result
