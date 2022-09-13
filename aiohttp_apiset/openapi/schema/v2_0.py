from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import Field

from .base import Model


class Ref(Model):
    """
    Represents a JSON reference ($ref)
    """
    ref: str = Field(alias='$ref')


class ExternalDocumentation(Model):
    description: Optional[str]
    url: str


class CollectionFormat(str, Enum):
    """
    Determines the format of the array.
    """
    csv = 'csv'
    ssv = 'ssv'
    tsv = 'tsv'
    pipes = 'pipes'
    multi = 'multi'


class PrimitiveType(str, Enum):
    string = 'string'
    number = 'number'
    integer = 'integer'
    boolean = 'boolean'
    array = 'array'


class Primitive(Model):
    """
    A limited subset of JSON-Schema's items object.

    It is used by parameter definitions that are not located in "body".
    """
    type_: Optional[PrimitiveType] = Field(alias='type')
    format_: Optional[str] = Field(alias='format')
    items: Optional['Primitive']
    collection_format: Optional[CollectionFormat]
    default: Optional[Any]
    maximum: Optional[float]
    exclusive_maximum: Optional[bool]
    minimum: Optional[float]
    exclusive_minimum: Optional[bool]
    max_length: Optional[int]
    min_length: Optional[int]
    pattern: Optional[str]
    max_items: Optional[int]
    min_items: Optional[int]
    unique_items: Optional[bool]
    enum: Optional[Set[Any]]
    multiple_of: Optional[float]


class Xml(Model):
    """
    A metadata object that allows for more fine-tuned XML model definitions.

    When using arrays, XML element names are not inferred (for singular/plural forms)
    and the name property should be used to add that information.
    """
    name: Optional[str]
    namespace: Optional[str]
    prefix: Optional[str]
    attribute: Optional[bool]
    wrapped: Optional[bool]


class SchemaType(str, Enum):
    array = 'array'
    boolean = 'boolean'
    integer = 'integer'
    null = 'null'
    number = 'number'
    object = 'object'
    string = 'string'


class Schema(Model):
    """
    The Schema Object allows the definition of input and output data types.

    See https://swagger.io/specification/v2/#schemaObject
    """
    ref: Optional[str] = Field(alias='$ref')
    format: Optional[str]
    title: Optional[str]
    description: Optional[str]
    default: Optional[Any]
    multiple_of: Optional[float]
    maximum: Optional[float]
    exclusive_maximum: Optional[bool]
    minimum: Optional[float]
    exclusive_minimum: Optional[bool]
    max_length: Optional[int]
    min_length: Optional[int]
    pattern: Optional[str]
    max_items: Optional[int]
    min_items: Optional[int]
    unique_items: Optional[bool]
    max_properties: Optional[int]
    min_properties: Optional[int]
    required: Optional[Set[str]]
    enum: Optional[List[Any]]
    additional_properties: Optional[Union[bool, Any]]
    type_: Optional[Union[SchemaType, Set[SchemaType]]] = Field(alias='type')
    items: Optional[Union['Schema', List['Schema']]]
    all_of: Optional[List['Schema']]
    properties: Optional[Dict[str, Union['Schema', Any]]]
    discriminator: Optional[str]
    read_only: Optional[bool]
    xml: Optional[Xml]
    external_docs: Optional[ExternalDocumentation]
    example: Optional[Any]


class HeaderType(str, Enum):
    string = 'string'
    number = 'number'
    integer = 'integer'
    boolean = 'boolean'
    array = 'array'


class Header(Model):
    type_: HeaderType = Field(alias='type')
    format_: Optional[str] = Field(alias='format')
    items: Optional[Primitive]
    collection_format: Optional[CollectionFormat]
    default: Optional[Any]
    maximum: Optional[float]
    exclusive_maximum: Optional[bool]
    minimum: Optional[float]
    exclusive_minimum: Optional[bool]
    max_length: Optional[int]
    min_length: Optional[int]
    pattern: Optional[str]
    max_items: Optional[int]
    min_items: Optional[int]
    unique_items: Optional[bool]
    enum: Optional[Set[Any]]
    multiple_of: Optional[float]
    description: Optional[str]


class ParameterLocation(str, Enum):
    body = "body"
    form_data = "formData"
    header = "header"
    path = "path"
    query = "query"


class ParameterType(str, Enum):
    string = "string"
    number = "number"
    integer = "integer"
    boolean = "boolean"
    array = "array"
    file = "file"


class Parameter(Model):
    """
    Describes a single parameter.

    A unique parameter is defined by a combination of a name and location.
    """
    name: str
    in_: ParameterLocation = Field(alias='in')
    description: Optional[str]
    required: Optional[bool]
    schema_: Optional[Schema]
    type_: Optional[ParameterType] = Field(alias='type')
    format_: Optional[str] = Field(alias='format')
    allow_empty_value: Optional[bool]
    items: Optional[Primitive]
    collection_format: Optional[CollectionFormat]
    default: Optional[Any]
    maximum: Optional[float]
    exclusive_maximum: Optional[bool]
    minimum: Optional[float]
    exclusive_minimum: Optional[bool]
    max_length: Optional[int]
    min_length: Optional[int]
    pattern: Optional[str]
    max_items: Optional[int]
    min_items: Optional[int]
    unique_items: Optional[bool]
    enum: Optional[Set[Any]]
    multiple_of: Optional[float]


class TransferProtocol(str, Enum):
    http = 'http'
    https = 'https'
    ws = 'ws'
    wss = 'wss'


class Response(Model):
    """Describes a single response from an API Operation."""
    description: str
    schema_: Optional[Schema]
    headers: Optional[Dict[str, Header]]
    examples: Optional[Dict[str, Any]]


SecurityRequirement = Dict[str, List[str]]
"""
Each name must correspond to a security scheme which is declared in the Security Definitions.
If the security scheme is of type "oauth2", then the value is a list of scope names required for the execution.
For other security scheme types, the array MUST be empty.
"""

SecurityRequirements = List[SecurityRequirement]
"""
A declaration of which security schemes are applied for this operation.

The list of values describes alternative security schemes that can be used
(that is, there is a logical OR between the security requirements).
This definition overrides any declared top-level security.
To remove a top-level security declaration, an empty array can be used.
"""


class Operation(Model):
    """
    Describes a single API operation on a path.
    """
    tags: Optional[Set[str]]
    summary: Optional[str]
    description: Optional[str]
    external_docs: Optional[ExternalDocumentation]
    operation_id: Optional[str]
    produces: Optional[Set[str]]
    consumes: Optional[Set[str]]
    parameters: Optional[List[Union[Ref, Parameter]]]
    responses: Dict[str, Union[Ref, Response]]
    schemes: Optional[Set[TransferProtocol]]
    deprecated: Optional[bool]
    security: Optional[SecurityRequirements]


class PathItem(Model):
    ref: Optional[str] = Field(alias='$ref')
    get: Optional[Operation]
    put: Optional[Operation]
    post: Optional[Operation]
    delete: Optional[Operation]
    options: Optional[Operation]
    head: Optional[Operation]
    patch: Optional[Operation]
    parameters: Optional[List[Union[Ref, Parameter]]]


class SecurityDefinitionType(str, Enum):
    basic = 'basic'
    api_key = 'apiKey'
    oauth2 = 'oauth2'


class SecurityDefinitionLocation(str, Enum):
    query = 'query'
    header = 'header'


class SecurityDefinitionFlow(str, Enum):
    implicit = 'implicit'
    password = 'password'
    application = 'application'
    access_code = 'accessCode'


class SecurityDefinition(Model):
    type_: SecurityDefinitionType = Field(alias='type')
    description: Optional[str]
    name: Optional[str]
    in_: Optional[SecurityDefinitionLocation] = Field(alias='in')
    flow: Optional[SecurityDefinitionFlow]
    authorization_url: Optional[str]
    token_url: Optional[str]
    scopes: Optional[Dict[str, str]]


SecurityDefinitions = Dict[str, SecurityDefinition]
"""
A declaration of the security schemes available to be used in the specification.

This does not enforce the security schemes on the operations
and only serves to provide the relevant details for each scheme.
"""


class Tag(Model):
    """
    Allows adding meta data to a single tag that is used by the Operation Object.

    It is not mandatory to have a Tag Object per tag used there.
    """
    name: str
    description: Optional[str]
    external_docs: Optional[ExternalDocumentation]


class Contact(Model):
    """Contact information for the exposed API."""
    name: Optional[str]
    url: Optional[str]
    email: Optional[str]


class License(Model):
    """License information for the exposed API."""
    name: str
    url: Optional[str]


class Info(Model):
    """
    The object provides metadata about the API.
    The metadata can be used by the clients if needed,
    and can be presented in the Swagger-UI for convenience.
    """
    title: str
    version: str
    description: Optional[str]
    terms_of_service: Optional[str]
    contact: Optional[Contact]
    license: Optional[License]


class SwaggerVersion(str, Enum):
    v2_0 = '2.0'


class Swagger(Model):
    swagger: SwaggerVersion
    info: Info
    host: Optional[str]
    base_path: Optional[str]
    schemes: Optional[Set[TransferProtocol]]
    consumes: Optional[Set[str]]
    produces: Optional[Set[str]]
    paths: Dict[str, PathItem]
    definitions: Optional[Dict[str, Schema]]
    parameters: Optional[Dict[str, Parameter]]
    responses: Optional[Dict[str, Response]]
    security: Optional[SecurityRequirements]
    security_definitions: Optional[SecurityDefinitions]
    tags: Optional[Set[Tag]]
    external_docs: Optional[ExternalDocumentation]
