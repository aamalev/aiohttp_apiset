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
    def load_yaml(cls, file_path: str):
        file_path = file_path.split('#')[0]
        data = cls.swagger_files.get(file_path)
        if not data:
            with open(file_path, encoding=cls._encoding) as f:
                data = yaml.load(f)
            cls.swagger_files[file_path] = data
        return data

    @classmethod
    def get_sub_swagger(cls, path, *, default=None):
        if isinstance(path, str):
            path = path.split('.')
        elif not isinstance(path, (list, tuple)):
            raise ValueError(path)
        fp = cls.get_swagger_filepath()[0]
        data = cls.load_yaml(fp)
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
