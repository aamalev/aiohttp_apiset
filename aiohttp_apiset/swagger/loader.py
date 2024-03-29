import abc
import json
import logging
import os
import sys
from collections import ChainMap, OrderedDict
from collections.abc import Hashable, Mapping
from functools import lru_cache
from itertools import chain
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple, Union  # noqa

import yaml.resolver
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode


try:
    from yaml.cyaml import CLoader as YamlLoader
except ImportError:
    from yaml import Loader as YamlLoader  # type: ignore

logger = logging.getLogger(__name__)


class FrozenDict(OrderedDict):
    def __init__(self, *args, **kwargs):
        self._frozen = False
        super().__init__(*args, **kwargs)

    def freeze(self):
        self._frozen = True

    def __setitem__(self, key, value):
        if self._frozen:
            raise RuntimeError('Frozen')
        return super().__setitem__(key, value)

    def __delitem__(self, key):
        if self._frozen:
            raise RuntimeError('Frozen')
        return super().__delitem__(key)

    def popitem(self, last: bool = True):
        if self._frozen:
            raise RuntimeError('Frozen')
        return super().popitem(last)

    __marker = object()

    def pop(self, key, default=__marker):
        if self._frozen:
            raise RuntimeError('Frozen')
        if default is self.__marker:
            return super().pop(key)
        else:
            return super().pop(key, default)

    def clear(self):
        if self._frozen:
            raise RuntimeError('Frozen')
        return super().clear()


class Loader(YamlLoader):
    def construct_yaml_map(self, node):
        data = FrozenDict()
        yield data
        value = self.construct_mapping(node)
        data.update(value)
        data.freeze()

    def construct_mapping(self, node, deep=False):
        if isinstance(node, MappingNode):
            self.flatten_mapping(node)
        mapping = FrozenDict()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, Hashable):
                raise ConstructorError(
                    "while constructing a mapping", node.start_mark,
                    "found unhashable key", key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        mapping.freeze()
        return mapping


Loader.add_constructor('tag:yaml.org,2002:map', Loader.construct_yaml_map)


@lru_cache(None)
def yaml_load(path: Path, encoding) -> dict:
    with path.open(encoding=encoding) as f:
        return yaml.load(f, Loader)


class SwaggerLoaderMixin:
    swagger_files = {}  # type: Dict[str, SchemaFile]
    _encoding = None  # type: Optional[str]

    @classmethod
    def get_swagger_ref(cls):
        if getattr(cls, 'swagger_ref'):
            return cls.swagger_ref
        f = os.path.join(
            cls.get_dir(),
            'swagger',
            cls.__name__.lower() + '.yaml')
        return f

    @classmethod
    def get_root_dir(cls):
        return cls.root_dir

    @classmethod
    def split_ref(cls, file_path):
        path = file_path.split('#')
        if len(path) == 2:
            file_path, path = path
            path = path.strip('/').split('/')
        else:
            path = []
        return file_path, path

    @classmethod
    def get_dir(cls):
        return os.path.dirname(sys.modules[cls.__module__].__file__)

    @classmethod
    def get_swagger_filepath(cls):
        fpath, ipath = cls.split_ref(cls.get_swagger_ref())
        if fpath.startswith('/'):
            fpath = fpath[1:]
            directory = cls.get_root_dir()
        else:
            directory = cls.get_dir()
        fpath = os.path.join(directory, fpath)
        return fpath, ipath

    @classmethod
    def load_file(cls, file_path: str, loader=None):
        file_path = file_path.split('#')[0]
        data = cls.swagger_files.get(file_path)
        if data is None:
            if loader is None:
                _, ext = os.path.splitext(file_path)
                ext = ext.lower()
                if ext == '.json':
                    loader = json.load
                elif ext in ('.yml', '.yaml'):
                    def loader(x):
                        return yaml.load(x, Loader)
                else:
                    raise ValueError('File type {} not supported'.format(ext))
            with open(file_path, encoding=cls._encoding) as f:
                data = loader(f)
            cls.swagger_files[file_path] = data
        return data

    @classmethod
    def get_sub_swagger(cls, path, *, default=None):
        if isinstance(path, str):
            path = path.split('.')
        elif not isinstance(path, (list, tuple)):
            raise ValueError(path)
        fp = cls.get_swagger_filepath()[0]
        data = cls.load_file(fp)
        for i in path:
            if i in data:
                data = data[i]
            else:
                return default
        return data


class Copyable(abc.ABC):
    def copy(self) -> dict:
        def conv(x):
            if isinstance(x, Copyable):
                return x.copy()
            elif isinstance(x, list):
                return [conv(o) for o in x]
            else:
                return x
        return OrderedDict((k, conv(v))
                           for k, v in self.items())  # type: ignore


class SchemaPointer(Copyable, Mapping):
    def __init__(self, schema_file, data):
        self._file = schema_file
        if '$ref' in data:
            self._data = schema_file(data['$ref'])
        else:
            self._data = data

    @property
    def data(self):
        if isinstance(self._data, SchemaPointer):
            return self._data.data
        elif isinstance(self._data, AllOf):
            return self._data.data
        else:
            return self._data

    @classmethod
    def factory(cls, f, data):
        if isinstance(data, list):
            return [cls.factory(f, i) for i in data]
        elif not isinstance(data, dict):
            return data
        elif 'allOf' in data:
            return AllOf.factory(f, data)
        elif '$ref' in data:
            return f(data['$ref'])
        else:
            return cls(f, data)

    def __getitem__(self, key):
        if key not in self._data:
            raise KeyError((key, self._data))
        return self.factory(self._file, self._data[key])

    def __iter__(self):
        yield from self._data

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return '<{cls} file={file} data={data!r}>'.format(
            cls=type(self).__name__,
            file=str(self._file),
            data=self._data,
        )


class AllOf(Copyable, ChainMap):
    def __init__(self, *maps, data=None):
        self.data = data
        super().__init__(*maps)

    @classmethod
    def factory(cls, file, data):
        maps = []
        for d in reversed(data['allOf']):
            maps.append(SchemaPointer.factory(file, d))
        if len(data) > 1:
            d = dict(data)
            d.pop('allOf')
            maps.append(d)
        return cls(*maps, data=data)

    def copy(self):
        result = {}
        for k, v in self.items():
            if k == 'required' and not v:
                continue
            elif isinstance(v, Copyable):
                result[k] = v.copy()
            else:
                result[k] = v
        return result


class SchemaFile(Copyable, Mapping):
    files = {}  # type: Dict[Path, SchemaFile]
    local_refs = {}  # type: Dict[str, SchemaFile]

    def __new__(cls, path, *args, **kwargs):
        if path in cls.files:
            return cls.files[path]
        else:
            inst = super().__new__(cls)
            inst.__init__(path, *args, **kwargs)
            cls.files[inst.path] = inst
            return inst

    def __init__(self, path, encoding='utf-8'):
        self._path = path
        self._encoding = encoding
        self._data = yaml_load(path, encoding=encoding)

    @property
    def data(self):
        return self._data

    @property
    def path(self):
        return self._path

    def find_path(self, path):
        if isinstance(path, str):
            s = path
            path = Path(path)
        else:
            s = ''

        if s.startswith('.'):
            pass
        elif path.exists() or path.is_absolute():
            return path
        return self._path.parent / path

    def factory(self, path):
        path = self.find_path(path)
        if path in self.files:
            return self.files[path]
        return type(self)(path)

    def __getitem__(self, item):
        if item in self._data:
            data = self._data[item]
        else:
            raise KeyError((item, self._data))
        return SchemaPointer.factory(self, data)

    def resolve_uri(self, uri):
        sharp = uri.find('#')
        if sharp >= 0:
            path, rel_path = uri.split('#', 1)
        else:
            path, rel_path = uri, ''

        if path:
            file = self.factory(path)
        else:
            file = self

        if not rel_path:
            rel_path = ()
        elif rel_path.startswith('/'):
            rel_path = rel_path.split('/')[1:]
        else:
            raise NotImplementedError(uri)

        return file, rel_path

    def __call__(self, item):
        data, rel_path = self.resolve_uri(item)

        pointer_file = data
        if not rel_path:
            return data
        for p in rel_path:
            try:
                data = data[p]
            except KeyError:
                raise KeyError(item, str(self._path))
        if self is pointer_file:
            self.local_refs[tuple(rel_path)] = data
        if not isinstance(data, Mapping):
            return data
        return SchemaPointer.factory(pointer_file, data)

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        yield from self._data

    def __repr__(self):
        return '<{cls} {path}>'.format(cls=type(self).__name__,
                                       path=getattr(self, '_path', None))


class IncludeSwaggerPaths(SchemaPointer):
    INCLUDE = '$include'

    @classmethod
    def _get_includes(cls, methods):
        if isinstance(methods, list):
            return (o[cls.INCLUDE] for o in methods if cls.INCLUDE in o)
        elif not isinstance(methods, Mapping):
            return ()
        elif cls.INCLUDE in methods:
            return methods[cls.INCLUDE],
        else:
            return ()

    def items(self):
        for pref, methods in self._data.items():
            if '$ref' in methods:
                yield pref, self._file(methods['$ref'])
                continue
            includes = self._get_includes(methods)
            if not includes:
                yield pref, SchemaPointer.factory(self._file, methods)
                continue
            for i in includes:
                f = self._file(i)
                basePath = f.get('basePath', '')
                for p, op in f['paths'].items():
                    yield pref + basePath + p, op

    def __iter__(self):
        for uri, methods in self.items():
            yield uri

    def __getitem__(self, item):
        data = sorted(self._data.items(), key=lambda x: -len(x[0]))
        for pref, methods in data:
            if item.startswith(pref):
                if '$ref' in methods and len(pref) == len(item):
                    return self._file(methods['$ref'])
                includes = self._get_includes(methods)
                if not includes and len(pref) == len(item):
                    return SchemaPointer.factory(self._file, methods)
                subitem = item[len(pref):]
                for i in includes:
                    f = self._file(i)
                    basePath = f.get('basePath', '')
                    i = subitem[len(basePath):]
                    try:
                        return f['paths'][i]
                    except KeyError:
                        pass
        raise KeyError(item)

    def __len__(self):
        raise NotImplementedError


class ExtendedSchemaFile(SchemaFile):
    include = IncludeSwaggerPaths
    files = {}  # type: Dict[Path, SchemaFile]
    local_refs = {}  # type: Dict[str, SchemaFile]

    @classmethod
    def class_factory(cls, *, include):
        inc = type(cls.include.__name__,
                   (cls.include,), {'INCLUDE': include})
        return type(cls.__name__, (cls,), {'include': inc})

    def __init__(
        self, path: Path,
        dirs: Sequence[Path] = (),
        encoding='utf-8',
    ):
        if not isinstance(path, Path):
            path = Path(path)
        if not path.is_absolute():
            pass
        elif dirs:
            for d in dirs:
                try:
                    path = path.relative_to(d)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError('Name must be relative path or child of dirs')
        else:
            dirs = path.parent,
            path = Path(path.name)
        self._dirs = tuple(dirs)
        self._cache = {}  # type: Dict[Union[Path, str], Path]
        path = self.find_path(path)
        super().__init__(path, encoding=encoding)
        self._ref_replaced = False

    def __getitem__(self, item):
        if item == 'paths':
            return self.include(self, self._data['paths'])
        return super().__getitem__(item)

    def factory(self, path):
        path = self.find_path(path)
        if path in self.files:
            return self.files[path]
        return type(self)(path, self._dirs)

    def find_path(self, path):
        if path in self._cache:
            return self._cache[path]
        else:
            key = path
        dirs = []
        if isinstance(path, str):
            if path.startswith('.'):
                dirs.append(self._path.parent)
            path = Path(path)
        elif path.parts[0].startswith('.'):
            dirs.append(self._path.parent)

        if dirs:
            pass
        elif path.exists():
            path = Path(os.path.normpath(str(path)))
            self._cache[key] = path
            return path
        elif path.is_absolute():
            raise FileNotFoundError(path)

        for i in chain(dirs, self._dirs):
            p = i / path
            if p.exists():
                p = Path(os.path.normpath(str(p)))
                self._cache[key] = p
                return p
        raise FileNotFoundError(path)

    def resolve(self):
        data = self._resolve_reference(self._data)
        paths = OrderedDict()
        for pref, methods in data['paths'].items():
            includes = self.include._get_includes(methods)
            if not includes:
                paths[pref] = methods
                continue
            for i in includes:
                sub = self.factory(i).resolve()
                basePath = sub.get('basePath', '')
                for uri, methods in sub['paths'].items():
                    paths[pref + basePath + uri] = methods
        data['paths'] = paths
        return data

    def _resolve_reference(self, data):
        # if self._ref_replaced and data is self._data:
        #     return data
        # self._ref_replaced = True

        if not isinstance(data, (dict, list)):
            return data

        is_dict = isinstance(data, dict)

        if is_dict and '$ref' in data:
            f, rel = self.resolve_uri(data['$ref'])

            if f is self:
                data = self._data
            else:
                data = f._resolve_reference(f._data)

            for p in rel:
                data = data[p]

            if f is self:
                self.local_refs[tuple(rel)] = data
            return data

        if is_dict:
            gen = data.items()
            data = dict(data)
        else:
            gen = enumerate(data)
            data = list(data)
        for k, v in gen:
            new_v = self._resolve_reference(v)
            if new_v is not v:
                data[k] = new_v
        return data


def get_ref(spec: dict, ref: str):
    url, ref = ref.split('#/')
    path = ref.split('/')
    current = spec
    for p in path:
        current = current[p]
    return current


def deref(data, spec: dict):
    """
    Return dereference data
    :param data:
    :param spec:
    :return:
    """
    if isinstance(data, Sequence):
        is_dict = False
        gen = enumerate(data)
    elif not isinstance(data, Mapping):
        return data
    elif '$ref' in data:
        return deref(get_ref(spec, data['$ref']), spec)
    else:
        is_dict = True
        gen = data.items()  # type: ignore

    result = None

    for k, v in gen:
        new_v = deref(v, spec)
        if new_v is not v:
            if result is not None:
                pass
            elif is_dict:
                result = data.copy()
            else:
                result = data[:]
            result[k] = new_v
    return result or data


class BaseLoader:
    def __init__(self, search_dirs=(), encoding='utf-8'):
        self._search_dirs = list(search_dirs)
        self._encoding = encoding

    @property
    def search_dirs(self):
        return self._search_dirs

    def add_search_dir(self, search_dir):
        self._search_dirs.append(Path(search_dir))

    def load(self, path):
        raise NotImplementedError

    def resolve_data(self, data):
        raise NotImplementedError


class FileLoader(BaseLoader):
    file_factory = ExtendedSchemaFile
    data_factory = SchemaPointer
    files = {}  # type: Dict[str, SchemaFile]
    local_refs = {}  # type: Dict[str, SchemaFile]

    def _update_mapping(self, f: SchemaFile) -> None:
        sd = sorted(self.search_dirs)
        for k, v in f.files.items():
            for d in sd:
                try:
                    self.files[str(k.relative_to(d))] = v
                    break
                except ValueError:
                    continue

    def _merge(self, refs, data):
        d = dict(data)
        for k, v in refs.items():
            if k not in d:
                d[k] = v
            elif not isinstance(v, Mapping):
                continue
            elif not isinstance(d[k], Mapping):
                continue
            else:
                d[k] = self._merge(v, d[k])
        return d

    def _nested_set(self, data, k, v):
        key, *k = k
        if not k:
            data[key] = v
            return data
        elif key not in data:
            data[key] = {}
        self._nested_set(data[key], k, v)
        return data

    def _set_local_refs(self, f):
        refs = {}
        for k, v in f.local_refs.items():
            self._nested_set(refs, k, v)
        self.local_refs.update(refs)
        return self._merge(refs, f)

    def __getitem__(self, item):
        return self.files[item]

    @classmethod
    def class_factory(cls, *, include):
        file = cls.file_factory.class_factory(include=include)
        return type(cls.__name__, (cls,), {'file_factory': file})

    def load(self, path):
        result = self.file_factory(
            path, dirs=self._search_dirs,
            encoding=self._encoding,
        )
        self.warm_up(result)
        self._update_mapping(result)
        return self._set_local_refs(result)

    def warm_up(self, file: SchemaFile) -> Mapping:
        file.copy()
        return file

    def resolve_data(self, data):
        result = self.data_factory.factory(self, data)
        self._update_mapping(self.file_factory)
        return result

    def __call__(self, ref):
        path, rel_path = ref.split('#', 1)
        f = self.file_factory(path, self._search_dirs, self._encoding)
        self._update_mapping(f)
        return f('#' + rel_path)


class DictLoader(FileLoader):
    def warm_up(self, file: SchemaFile) -> Mapping:
        return file.copy()

    def __call__(self, ref):
        pointer = super().__call__(ref)
        if isinstance(pointer, Copyable):
            return pointer.copy()
        elif isinstance(pointer, list):
            return [p.copy() for p in pointer]
        else:
            return pointer
