from ..schema import v2_0 as schema
from .base import BaseLoader


class Loader(BaseLoader[schema.Swagger]):
    DEFAULT_DATA = {
        'swagger': '2.0',
        'info': {
            'title': 'API',
            'version': '1.0'
        }
    }
    REQUEST_METHODS = ['get', 'put', 'post', 'delete', 'options', 'head', 'patch']
    operation_factory = schema.Operation
    path_item_factory = schema.PathItem
