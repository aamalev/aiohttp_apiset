"""
Contains unified v2/v3 OpenAPI specification models for router configuration
"""
import json
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from urllib.parse import unquote

from pydantic import BaseModel, Extra, Field

from .utils import pairwise


class Model(BaseModel, extra=Extra.allow):
    def __repr_args__(self):
        return [
            (key, value)
            for key, value in self.__dict__.items()
            if value is not None
        ]

    def dict(self, **kwargs):
        kwargs.setdefault('by_alias', True)
        kwargs.setdefault('exclude_unset', True)
        kwargs.setdefault('exclude_none', True)
        return super().dict(**kwargs)


class Schema(Model):
    """
    JSON Schema: A Media Type for Describing JSON Documents

    https://json-schema.org/draft/2020-12/json-schema-core.html
    """

    id_: Optional[str] = Field(alias='$id')
    schema_: Optional[str] = Field(alias='$schema')
    ref: Optional[str] = Field(alias='$ref')
    anchor: Optional[str] = Field(alias='$anchor')
    dynamic_ref: Optional[str] = Field(alias='$dynamicRef')
    dynamic_anchor: Optional[str] = Field(alias='$dynamicAnchor')
    vocabulary: Optional[Dict[str, Any]] = Field(alias='$vocabulary')
    comment: Optional[str] = Field(alias='$comment')
    defs: Optional[Dict[str, Any]] = Field(alias='$defs')
    format_: Optional[str] = Field(alias='format')
    title: Optional[str]
    description: Optional[str]
    default: Any
    deprecated: Optional[bool]
    read_only: Optional[bool] = Field(alias='readOnly')
    write_only: Optional[bool] = Field(alias='writeOnly')
    examples: Optional[List[Any]]
    unevaluated_items: Optional['Schema'] = Field(alias='unevaluatedItems')
    unevaluated_properties: Optional['Schema'] = Field(alias='unevaluatedProperties')
    type_: Optional[Union[str, List[str]]] = Field(alias='type')
    const: Any
    enum: Optional[List[Any]]
    multiple_of: Optional[Union[int, float]] = Field(alias='multipleOf')
    maximum: Optional[Union[int, float]]
    exclusive_maximum: Optional[Union[int, float]] = Field(alias='exclusiveMaximum')
    minimum: Optional[Union[int, float]]
    exclusive_minimum: Optional[Union[int, float]] = Field(alias='exclusiveMinimum')
    max_length: Optional[int] = Field(alias='maxLength')
    min_length: Optional[int] = Field(alias='minLength')
    pattern: Optional[str]
    max_items: Optional[int] = Field(alias='maxItems')
    min_items: Optional[int] = Field(alias='minItems')
    unique_items: Optional[bool] = Field(alias='uniqueItems')
    max_contains: Optional[int] = Field(alias='maxContains')
    min_contains: Optional[int] = Field(alias='minContains')
    max_properties: Optional[int] = Field(alias='maxProperties')
    min_properties: Optional[int] = Field(alias='minProperties')
    required: Optional[List[str]]
    dependent_required: Optional[Dict[str, List[str]]] = Field(alias='dependentRequired')
    content_encoding: Optional[str] = Field(alias='contentEncoding')
    content_media_type: Optional[str] = Field(alias='contentMediaType')
    content_schema: Optional['Schema'] = Field(alias='contentSchema')
    prefix_items: Optional[List['Schema']] = Field(alias='prefixItems')
    items: Optional['Schema']
    contains: Optional['Schema']
    additional_properties: Optional[Union[bool, 'Schema']] = Field(alias='additionalProperties')
    properties: Optional[Dict[str, 'Schema']]
    pattern_properties: Optional[Dict[str, 'Schema']] = Field(alias='patternProperties')
    dependent_schemas: Optional[Dict[str, 'Schema']] = Field(alias='dependentSchemas')
    property_names: Optional['Schema'] = Field(alias='propertyNames')
    if_: Optional['Schema'] = Field(alias='if')
    then: Optional['Schema']
    else_: Optional['Schema'] = Field(alias='else')
    all_of: Optional[List['Schema']] = Field(alias='allOf')
    any_of: Optional[List['Schema']] = Field(alias='anyOf')
    one_of: Optional[List['Schema']] = Field(alias='oneOf')
    not_: Optional['Schema'] = Field(alias='not')


class ParameterLocation(str, Enum):
    cookie = 'cookie'
    header = 'header'
    path = 'path'
    query = 'query'


class ParameterStyle(str, Enum):
    matrix = 'matrix'
    label = 'label'
    form = 'form'
    simple = 'simple'
    space_delimited = 'spaceDelimited'
    pipe_delimited = 'pipeDelimited'
    deep_object = 'deepObject'
    tab_delimited = 'tabDelimited'
    json = 'json'


class Parameter(Model):
    name: str
    location: ParameterLocation
    required: bool = False
    allow_empty_value: bool = False
    style: ParameterStyle
    explode: bool
    data: Optional[Schema] = None

    @classmethod
    def cookie(cls, name: str) -> 'Parameter':
        return cls(
            name=name,
            location=ParameterLocation.cookie,
            style=ParameterStyle.form,
            explode=True
        )

    @classmethod
    def header(cls, name: str) -> 'Parameter':
        return cls(
            name=name,
            location=ParameterLocation.header,
            style=ParameterStyle.simple,
            explode=False
        )

    @classmethod
    def path(cls, name: str) -> 'Parameter':
        return cls(
            name=name,
            location=ParameterLocation.path,
            style=ParameterStyle.simple,
            explode=False
        )

    @classmethod
    def query(cls, name: str) -> 'Parameter':
        return cls(
            name=name,
            location=ParameterLocation.query,
            style=ParameterStyle.form,
            explode=True
        )

    def set_required(self, required: bool) -> 'Parameter':
        self.required = required
        return self

    def set_style(self, style: ParameterStyle) -> 'Parameter':
        self.style = style
        return self

    def set_explode(self, explode: bool) -> 'Parameter':
        self.explode = explode
        return self

    def set_schema(self, **kwargs: Any) -> 'Parameter':
        self.data = Schema(**kwargs)
        return self

    def set_allow_empty_value(self, flag: bool) -> 'Parameter':
        self.allow_empty_value = flag
        return self

    def parse_array_values(self, raw_values: str) -> List[str]:
        if self.style == ParameterStyle.matrix:
            if self.explode:
                # ;color=blue;color=black;color=brown
                values = raw_values.lstrip(';').split(';')
                values = [i.split('=')[-1] for i in values]
            else:
                # ;color=blue,black,brown
                values = raw_values.split('=')[-1].split(',')
        elif self.style == ParameterStyle.label:
            # .blue.black.brown
            values = raw_values.lstrip('.').split('.')
        elif self.style == ParameterStyle.form:
            if self.explode:
                # color=blue&color=black&color=brown
                values = raw_values.split('&')
                values = [i.split('=')[-1] for i in values]
            else:
                # color=blue,black,brown
                values = raw_values.split('=')[-1].split(',')
        elif self.style == ParameterStyle.simple:
            # blue,black,brown
            values = raw_values.split(',')
        elif self.style == ParameterStyle.space_delimited:
            # blue%20black%20brown
            values = unquote(raw_values).split(' ')
        elif self.style == ParameterStyle.pipe_delimited:
            values = raw_values.split('|')
        elif self.style == ParameterStyle.deep_object:
            raise ValueError('Deep object style is not supported')
        elif self.style == ParameterStyle.tab_delimited:
            values = raw_values.split('\t')
        else:
            raise NotImplementedError()  # pragma: no cover
        return values

    def parse_object_properties(self, raw_data: str) -> Dict[str, str]:
        if self.style == ParameterStyle.matrix:
            if self.explode:
                # matrix,true: ;R=100;G=200;B=150
                parts = raw_data.lstrip(';').split(';')
                pairs = [i.split('=') for i in parts]
                result = dict(pairs)
            else:
                # matrix,false: ;color=R,100,G,200,B,150
                parts = raw_data.split('=')[-1].split(',')
                result = dict(pairwise(parts))
        elif self.style == ParameterStyle.label:
            if self.explode:
                # label,true: .R=100.G=200.B=150
                parts = raw_data.lstrip('.').split('.')
                pairs = [i.split('=') for i in parts]
                result = dict(pairs)
            else:
                # label,false: .R.100.G.200.B.150
                parts = raw_data.lstrip('.').split('.')
                result = dict(pairwise(parts))
        elif self.style == ParameterStyle.form:
            if self.explode:
                # from,true: R=100&G=200&B=150
                parts = raw_data.split('&')
                pairs = [i.split('=') for i in parts]
                result = dict(pairs)
            else:
                # form,false: color=R,100,G,200,B,150
                parts = raw_data.split('=')[-1].split(',')
                result = dict(pairwise(parts))
        elif self.style == ParameterStyle.simple:
            if self.explode:
                # simple,true: R=100,G=200,B=150
                parts = raw_data.split(',')
                pairs = [i.split('=') for i in parts]
                result = dict(pairs)
            else:
                # simple,false: R,100,G,200,B,150
                parts = raw_data.split(',')
                result = dict(pairwise(parts))
        elif self.style == ParameterStyle.space_delimited:
            # spaceDelimited: R%20100%20G%20200%20B%20150
            parts = unquote(raw_data).split(' ')
            result = dict(pairwise(parts))
        elif self.style == ParameterStyle.pipe_delimited:
            # pipeDelimited: R|100|G|200|B|150
            parts = raw_data.split('|')
            result = dict(pairwise(parts))
        elif self.style == ParameterStyle.deep_object:
            # deepObject: color[R]=100&color[G]=200&color[B]=150
            parts = raw_data.split('&')
            pairs = [i.split('=') for i in parts]
            offset = len('{}['.format(self.name)) + 1
            result = {k[offset:-1]: v for k, v in pairs}
        elif self.style == ParameterStyle.tab_delimited:
            parts = raw_data.split('\t')
            result = dict(pairwise(parts))
        elif self.style == ParameterStyle.json:
            result = json.loads(unquote(raw_data))
        else:
            raise NotImplementedError()  # pragma: no cover
        return result


Parameters = List[Parameter]


class Header(Model):
    name: str
    required: bool = False
    allow_empty_value: bool = False
    style: Optional[ParameterStyle] = None
    explode: Optional[bool] = None
    data: Optional[Schema] = None


Headers = List[Header]


class Encoding(Model):
    property_name: str
    headers: Headers
    content_type: Optional[str] = None
    style: Optional[ParameterStyle] = None
    explode: Optional[bool] = None
    allow_reserved: Optional[bool] = None


Encodings = List[Encoding]


class MediaContentType(str, Enum):
    any_ = '*/*'
    binary = 'application/octet-stream'
    json = 'application/json'
    multipart = 'multipart/form-data'
    text = 'text/plain'
    urlencoded = 'application/x-www-form-urlencoded'


class MediaType(Model):
    name: Optional[str] = None
    encodings: Encodings
    content_type: Union[MediaContentType, str]
    data: Optional[Schema] = None


MediaTypes = List[MediaType]


class Payload(Model):
    media_types: MediaTypes
    required: bool


class OperationMethod(str, Enum):
    delete = 'DELETE'
    get = 'GET'
    head = 'HEAD'
    options = 'OPTIONS'
    put = 'PUT'
    post = 'POST'
    patch = 'PATCH'
    trace = 'TRACE'


class Operation(Model):
    method: OperationMethod
    handler_name: Optional[str] = None
    operation_id: Optional[str] = None
    parameters: Parameters
    payload: Optional[Payload] = None


Operations = List[Operation]


class Path(Model):
    url: str
    location_name: Optional[str] = None
    operations: Operations


Paths = List[Path]


class OpenAPI(Model):
    base_path: str
    paths: Paths
