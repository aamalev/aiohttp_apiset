import json
import os
from copy import deepcopy
from enum import Enum
from functools import partial
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Mapping,
    Optional,
    Sequence,
    TextIO,
    Type,
    TypeVar,
    Union,
)
from typing import get_args as get_type_args

import yaml
from pydantic import BaseModel, parse_obj_as

from ...json_encoder import JsonEncoder as BaseJsonEncoder


JsonEncoder = BaseJsonEncoder.class_factory()
YamlLoader: Type[yaml.Loader] = getattr(yaml, 'CLoader', yaml.Loader)


class YamlDumper(yaml.SafeDumper):
    def represent_data(self, data: Any) -> Any:
        if isinstance(data, (set, tuple)):
            return super().represent_data(list(data))
        if isinstance(data, Enum):
            return super().represent_data(data.value)
        return super().represent_data(data)


DEFAULT_ENCODING = 'utf-8'
EXT_JSON = ['.json']
EXT_YAML = ['.yml', '.yaml']
INCLUDE = '$include'


ModelT = TypeVar('ModelT', bound=BaseModel)
RefT = TypeVar('RefT')


class ExportFormat(str, Enum):
    json = 'json'
    yaml = 'yaml'


class BaseLoader(Generic[ModelT]):
    """
    :param encoding: Default file encoding
    """

    DEFAULT_DATA: Dict[str, Any] = {}
    REQUEST_METHODS: List[str] = []
    operation_factory: Optional[Callable]
    path_item_factory: Optional[Callable]

    def __init__(self, encoding: str = DEFAULT_ENCODING):
        self._directories: List[Path] = []
        self._specification: Optional[ModelT] = None
        self._specification_proxy: Optional[MappingProxy[ModelT]] = None
        self._includes: Dict[str, Any] = {}
        self._encoding = encoding

    @classmethod
    def default(cls) -> 'BaseLoader[ModelT]':
        loader = cls()
        loader.load_default()
        return loader

    @property
    def specification(self) -> Optional[ModelT]:
        return self._specification

    @property
    def specification_factory(self) -> Type[ModelT]:
        orig_bases = getattr(self, '__orig_bases__', None)
        assert orig_bases
        generic_cls = orig_bases[0]
        type_args = get_type_args(generic_cls)
        assert type_args
        factory = type_args[0]
        return factory

    def add_directory(self, path: Union[str, Path]):
        """
        Adds a directory to search

        :param path: Path to directory
        """
        if not isinstance(path, Path):
            path = Path(path)
        if not path.is_dir():
            raise ValueError('No such directory: {}'.format(path))
        if path not in self._directories:
            self._directories.append(path)

    def load_default(self):
        """
        Loads a root specification object with default values
        """
        if self._specification is not None:
            raise RuntimeError('Specification already loaded')

        data = deepcopy(self.DEFAULT_DATA)
        data['paths'] = {}
        self._specification = self.specification_factory(**data)
        self._specification_proxy = MappingProxy(self._specification)

    def load(self, filename: Union[str, Path]):
        """
        Loads a root specification object

        :param filename: Name of the file to load from
        """
        if self._specification is not None:
            raise RuntimeError('Specification already loaded')

        path = self._find_path(filename)
        self.add_directory(path.parent)

        data = self._read_file(filename)
        _assert_mapping(data)
        data['paths'] = self._convert_paths(data.get('paths'))
        self._specification = self.specification_factory(**data)
        self._specification_proxy = MappingProxy(self._specification)

    def add_operation(self, url: str, method: str, operation_data: Dict[str, Any]) -> Any:
        """
        Adds an operation to root specification object

        :param url: PathItem url
        :param method: Operation method
        :param operation: Operation itself
        """
        assert self.operation_factory is not None
        assert self.path_item_factory is not None

        if self._specification is None:
            raise RuntimeError('Specification is not loaded')

        paths = getattr(self._specification, 'paths')
        operation = self.operation_factory(**operation_data)
        if url in paths:
            path_item = paths[url]
        else:
            path_item = self.path_item_factory()
            paths[url] = path_item

        method = method.lower()
        assert method in self.REQUEST_METHODS
        setattr(path_item, method, operation)

        return operation

    def dump(self, filename: Optional[str] = None, export_format: ExportFormat = ExportFormat.json) -> str:
        """
        Dumps specification to string

        :param filename: Filename to dump, root specification object used if filename is not specified
        :param export_format: Export format: YAML or JSON
        """
        if filename is None:
            if self._specification is None:
                raise RuntimeError('Specification is not loaded')
            data = self._specification.dict(by_alias=True, exclude_unset=True)
        else:
            data = self._include(filename)
        if export_format == ExportFormat.json:
            encoder = JsonEncoder.dumps
        elif export_format == ExportFormat.yaml:
            encoder = partial(yaml.dump, Dumper=YamlDumper)
        else:
            raise NotImplementedError()  # pragma: no cover
        return encoder(data)

    def resolve_ref(self, object_type: Type[RefT], ref: str) -> RefT:
        """
        Returns data under given reference

        :param object_type: Type of data under reference
        :param ref: Reference to resolve
        :param filename: File to search data in
        """
        sharp_position = ref.find('#')
        if sharp_position >= 0:
            include_path, object_path = ref.split('#', 1)
        else:
            include_path, object_path = ref, ''

        object_path = object_path.strip('/')

        if include_path:
            try:
                data = self._include(include_path)
            except FileNotFoundError as exc:
                raise ValueError('Reference not found: {}'.format(ref)) from exc
        else:
            if not object_path:
                raise ValueError('Reference points to root object: {}'.format(ref))
            if self._specification_proxy is None:
                raise RuntimeError('Specification is not loaded')
            data = self._specification_proxy

        if object_path:
            for key in object_path.split('/'):
                try:
                    data = data[key]
                except (TypeError, KeyError):
                    raise KeyError('Reference not exists: {}, last key: {}'.format(ref, key)) from None

        return parse_obj_as(object_type, data)

    def _include(self, filename: Union[str, Path]) -> Any:
        key = str(filename)
        if key not in self._includes:
            data = self._read_file(filename)
            self._includes[key] = data
        return self._includes[key]

    def _find_path(self, filename: Union[str, Path]) -> Path:
        for i in self._directories:
            result = i / filename
            if result.is_file():
                return Path(os.path.normpath(result))
        raise FileNotFoundError('No such file: {}'.format(filename))

    def _read_file(self, filename: Union[str, Path]) -> Any:
        path = self._find_path(filename)
        decoder = _resolve_decoder(path)
        with path.open(encoding=self._encoding) as f:
            data = decoder(f)
        return self._convert_relative_references(str(filename), data)

    def _convert_relative_references(self, filename: str, data: Any) -> Any:
        """
        Makes references absolute in order to simplify resolver
        """
        if isinstance(data, Mapping):
            result = {}
            for k, v in data.items():
                if k == '$ref' and isinstance(v, str) and v.startswith('#'):
                    v = '{}/{}'.format(filename, v)
                else:
                    v = self._convert_relative_references(filename, v)
                result[k] = v
            return result

        if isinstance(data, list):
            return [self._convert_relative_references(filename, i) for i in data]

        return data

    def _convert_paths(self, raw_data: Any, url_prefix: Optional[str] = None) -> Mapping[str, Mapping]:
        if raw_data is None:
            return {}
        if url_prefix is None:
            url_prefix = ''
        _assert_mapping(raw_data)
        return self._convert_paths_any(url_prefix, raw_data)

    def _convert_paths_any(self, url_prefix: str, raw_data: Any) -> Mapping[str, Mapping]:
        result: Dict[str, Mapping] = {}
        for item_prefix, item in raw_data.items():
            item_prefix = url_prefix + item_prefix
            if isinstance(item, Sequence):
                result.update(self._convert_paths_sequence(item_prefix, item))
            elif isinstance(item, Mapping):
                result.update(self._convert_paths_mapping(item_prefix, item))
            else:
                raise TypeError('Unknown path item type: {}'.format(type(item).__name__))
        return result

    def _convert_paths_sequence(self, url_prefix: str, sequence: Sequence[Any]) -> Mapping[str, Mapping]:
        result: Dict[str, Mapping] = {}
        for item in sequence:
            _assert_mapping(item)
            result.update(self._convert_paths_mapping(url_prefix, item))
        return result

    def _convert_paths_mapping(self, url_prefix: str, mapping: Mapping[str, Any]) -> Mapping[str, Mapping]:
        result: Dict[str, Mapping] = {}
        if INCLUDE in mapping:
            data = self._read_file(mapping[INCLUDE])
            _assert_mapping(data)
            result.update(self._convert_paths_include(url_prefix, data))
        else:
            result[url_prefix] = mapping
        return result

    def _convert_paths_include(self, url_prefix: str, raw_data: Mapping[str, Any]) -> Mapping[str, Mapping]:
        paths = raw_data.get('paths')
        _assert_mapping(paths)
        url_prefix = url_prefix + raw_data.get('basePath', '')
        return self._convert_paths_any(url_prefix, paths)


def _assert_mapping(obj: Any):
    if not isinstance(obj, Mapping):
        raise TypeError('Expects mapping, got {}'.format(type(obj).__name__))


Decoder = Callable[[TextIO], Any]


def _decode_json(source: TextIO) -> Any:
    return json.load(source)


def _decode_yaml(source: TextIO) -> Any:
    return yaml.load(source, YamlLoader)


def _resolve_decoder(path: Path) -> Decoder:
    ext = path.suffix.lower()
    if ext in EXT_JSON:
        decoder = _decode_json
    elif ext in EXT_YAML:
        decoder = _decode_yaml
    else:
        raise ValueError('Unknown file format: {}'.format(path))
    return decoder


class MappingProxy(Generic[ModelT]):
    def __init__(self, model: ModelT):
        self._model = model

    def __getitem__(self, key: str) -> Any:
        try:
            value = getattr(self._model, key)
        except AttributeError:
            raise KeyError(key)
        if isinstance(value, BaseModel):
            value = MappingProxy(value)
        return value
