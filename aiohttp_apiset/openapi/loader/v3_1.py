from ..schema import v3_1 as schema
from .base import BaseLoader


class Loader(BaseLoader[schema.OpenAPI]):
    DEFAULT_DATA = {
        'openapi': '3.1.0',
        'info': {
            'title': 'API',
            'version': '1.0'
        }
    }
    REQUEST_METHODS = ['get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace']
    operation_factory = schema.Operation
    path_item_factory = schema.PathItem
