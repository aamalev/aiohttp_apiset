import json
import os
import sys

import yaml


class SwaggerLoaderMixin:
    swagger_files = {}
    _encoding = None

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
                    loader = yaml.load
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

    @property
    def swagger_path(self):
        sw_prop = '_swagger_path'
        data = getattr(self, sw_prop, None)
        if data:
            return data
        fp, path = self.get_swagger_filepath()
        data = self.get_sub_swagger(path)
        setattr(self, sw_prop, data)
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
    is_dict = isinstance(data, dict)

    if is_dict and '$ref' in data:
        return deref(get_ref(spec, data['$ref']), spec)

    if not isinstance(data, (dict, list)):
        return data

    result = None
    gen = data.items() if is_dict else enumerate(data)
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
