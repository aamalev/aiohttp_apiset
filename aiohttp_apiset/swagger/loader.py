import os
import sys

import yaml


class SwaggerLoaderMixin:
    swagger_files = {}

    def get_swagger_ref(self):
        return self.swagger_ref

    def get_root_dir(self):
        return self.root_dir

    def split_ref(self, file_path):
        path = file_path.split('#')
        if len(path) == 2:
            file_path, path = path
            path = path.strip('/').split('/')
        else:
            path = []
        return file_path, path

    def get_swagger_filepath(self):
        fpath, ipath = self.split_ref(self.get_swagger_ref())
        if fpath.startswith('/'):
            fpath = fpath[1:]
            directory = self.get_root_dir()
        else:
            directory = os.path.dirname(sys.modules[self.__module__].__file__)
        fpath = os.path.join(directory, fpath)
        return fpath, ipath

    def load_yaml(self, file_path: str):
        file_path = file_path.split('#')[0]
        data = self.swagger_files.get(file_path)
        if not data:
            with open(file_path) as f:
                data = yaml.load(f)
            self.swagger_files[file_path] = data
        return data

    def get_sub_swagger(self, path: list):
        fp, path = self.get_swagger_filepath()
        data = self.load_yaml(fp)
        for i in path:
            data = data[i]
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
