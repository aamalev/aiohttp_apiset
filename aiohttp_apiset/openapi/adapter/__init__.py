from typing import cast

from ...schema import OpenAPI
from .. import loader
from .. import schema as openapi_schema
from .v2_0 import convert as convert_v2_0
from .v3_1 import convert as convert_v3_1


__all__ = ['OpenAPI', 'convert']


def convert(obj: loader.BaseLoader) -> OpenAPI:
    factory = obj.specification_factory
    if factory is openapi_schema.v2_0.Swagger:
        return convert_v2_0(cast(loader.v2_0.Loader, obj))
    if factory is openapi_schema.v3_1.OpenAPI:
        return convert_v3_1(cast(loader.v3_1.Loader, obj))
    raise NotImplementedError()  # pragma: no cover
